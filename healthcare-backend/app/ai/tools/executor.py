"""Tool adapters that validate calls and delegate all work to existing services."""

from __future__ import annotations

from datetime import datetime, time, timedelta, timezone
from typing import Any

from pydantic import ValidationError

from app.ai.schemas import BookingConfirmation, ToolResult
from app.ai.tools.confirmation import create_booking_confirmation, decode_booking_confirmation
from app.ai.tools.registry import TOOL_ARGUMENT_MODELS
from app.ai.tools.schemas import (
    AvailableSlotsArgs,
    CreateBookingArgs,
    HandoffToStaffArgs,
    ListDoctorsArgs,
    SearchSpecialtyArgs,
)
from app.appointments.schemas import AppointmentCreate
from app.appointments.service import AppointmentService
from app.auth.context import ActorContext
from app.core.config import Settings
from app.core.errors import BadRequestError, ConflictError
from app.doctors.service import DoctorService
from app.handoffs.schemas import HandoffCreate
from app.handoffs.service import HandoffService
from app.handoffs.realtime import handoff_connections
from app.schedules.service import ScheduleService
from app.specialties.service import SpecialtyService

VIETNAM_TIMEZONE = timezone(timedelta(hours=7))


class ToolExecutor:
    """Identity-safe adapter; deliberately contains no ORM or SQL access."""

    def __init__(self, session: Any, settings: Settings) -> None:
        self.settings = settings
        self.specialties = SpecialtyService(session)
        self.doctors = DoctorService(session)
        self.schedules = ScheduleService(session)
        self.appointments = AppointmentService(session)
        self.handoffs = HandoffService(session)

    async def execute(
        self, name: str, raw_arguments: dict[str, Any], actor: ActorContext
    ) -> ToolResult:
        argument_model = TOOL_ARGUMENT_MODELS.get(name)
        if argument_model is None:
            raise BadRequestError("The requested tool is not supported.", "unknown_tool")
        try:
            arguments = argument_model.model_validate(raw_arguments)
        except ValidationError as exc:
            raise BadRequestError(
                "Tool arguments are missing or invalid.", "invalid_tool_arguments"
            ) from exc

        if isinstance(arguments, SearchSpecialtyArgs):
            rows = self.specialties.search(arguments.query)
            return ToolResult(
                name=name,
                status="SUCCESS",
                data={
                    "items": [
                        {
                            "id": str(item.id),
                            "code": item.code,
                            "name": item.name,
                            "description": item.description,
                        }
                        for item in rows
                    ],
                    "count": len(rows),
                },
            )
        if isinstance(arguments, ListDoctorsArgs):
            rows = self.doctors.list(
                specialty_id=arguments.specialty_id,
                active_only=arguments.filters.active_only,
            )
            return ToolResult(
                name=name,
                status="SUCCESS",
                data={
                    "items": [
                        {
                            "id": str(item.id),
                            "full_name": item.user.full_name,
                            "specialty_id": str(item.specialty_id),
                            "specialty_name": item.specialty.name,
                            "biography": item.biography,
                        }
                        for item in rows
                    ],
                    "count": len(rows),
                },
            )
        if isinstance(arguments, AvailableSlotsArgs):
            day_start = datetime.combine(arguments.date, time.min, VIETNAM_TIMEZONE)
            day_end = day_start + timedelta(days=1)
            rows = self.schedules.available_slots(
                day_start.astimezone(timezone.utc),
                day_end.astimezone(timezone.utc),
                doctor_id=arguments.doctor_id,
            )
            return ToolResult(
                name=name,
                status="SUCCESS",
                data={
                    "items": [
                        {
                            "slot_id": str(item.id),
                            "doctor_id": str(item.schedule.doctor.id),
                            "doctor_name": item.schedule.doctor.user.full_name,
                            "specialty_name": item.schedule.doctor.specialty.name,
                            "start_at": item.start_at.isoformat(),
                            "end_at": item.end_at.isoformat(),
                        }
                        for item in rows
                    ],
                    "count": len(rows),
                },
            )
        if isinstance(arguments, CreateBookingArgs):
            actor.require_any_role("PATIENT")
            slot = self.schedules.get_slot(arguments.slot_id)
            if slot.schedule.status.value != "ACTIVE" or slot.status.value != "AVAILABLE":
                raise ConflictError("The selected slot is not available.", "slot_unavailable")
            if slot.start_at <= datetime.now(timezone.utc):
                raise BadRequestError("Past slots cannot be booked.", "slot_in_past")
            doctor = slot.schedule.doctor
            confirmation = BookingConfirmation(
                confirmation_token=create_booking_confirmation(
                    actor.user_id, slot.id, self.settings
                ),
                slot_id=slot.id,
                doctor_id=doctor.id,
                doctor_name=doctor.user.full_name,
                specialty_id=doctor.specialty.id,
                specialty_name=doctor.specialty.name,
                start_at=slot.start_at,
                end_at=slot.end_at,
            )
            return ToolResult(
                name=name,
                status="CONFIRMATION_REQUIRED",
                data=confirmation.model_dump(mode="json"),
            )
        if isinstance(arguments, HandoffToStaffArgs):
            request = self.handoffs.create(
                HandoffCreate(reason=arguments.reason, source="CHATBOT"), actor
            )
            await handoff_connections.publish_handoff("handoff.created", request)
            return ToolResult(
                name=name,
                status="SUCCESS",
                data={
                    "handoff_id": str(request.id),
                    "status": request.status.value,
                    "message": "Yêu cầu đã được chuyển cho nhân viên.",
                },
            )
        raise BadRequestError("The requested tool is not supported.", "unknown_tool")

    def confirm_booking(self, token: str, actor: ActorContext):
        slot_id = decode_booking_confirmation(token, actor.user_id, self.settings)
        return self.appointments.create(AppointmentCreate(schedule_slot_id=slot_id), actor)

    async def create_risk_handoff(
        self, rule_codes: tuple[str, ...], actor: ActorContext
    ) -> ToolResult:
        """Internal safety adapter; deliberately not exposed as a Gemini function."""
        request = self.handoffs.create_risk_alert(rule_codes, actor)
        await handoff_connections.publish_handoff("handoff.created", request)
        return ToolResult(
            name="risk_handoff",
            status="SUCCESS",
            data={
                "handoff_id": str(request.id),
                "status": request.status.value,
                "priority": request.priority.value,
                "message": "Yêu cầu hỗ trợ ưu tiên đã được ghi nhận.",
            },
        )

