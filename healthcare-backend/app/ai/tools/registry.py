"""Gemini declarations and the only permitted Phase 9 tool names."""

from google.genai import types

from app.ai.tools.schemas import (
    AvailableSlotsArgs,
    CreateBookingArgs,
    HandoffToStaffArgs,
    ListDoctorsArgs,
    SearchSpecialtyArgs,
    ToolArguments,
)

TOOL_ARGUMENT_MODELS: dict[str, type[ToolArguments]] = {
    "search_specialty": SearchSpecialtyArgs,
    "list_doctors": ListDoctorsArgs,
    "available_slots": AvailableSlotsArgs,
    "create_booking": CreateBookingArgs,
    "handoff_to_staff": HandoffToStaffArgs,
}

TOOL_DECLARATIONS = [
    types.FunctionDeclaration(
        name="search_specialty",
        description="Tìm chuyên khoa đang hoạt động theo tên, mã hoặc mô tả.",
        parameters_json_schema=SearchSpecialtyArgs.model_json_schema(),
    ),
    types.FunctionDeclaration(
        name="list_doctors",
        description="Liệt kê bác sĩ thật thuộc một chuyên khoa đã chọn.",
        parameters_json_schema=ListDoctorsArgs.model_json_schema(),
    ),
    types.FunctionDeclaration(
        name="available_slots",
        description="Tra cứu các slot còn trống của bác sĩ trong một ngày theo giờ Việt Nam.",
        parameters_json_schema=AvailableSlotsArgs.model_json_schema(),
    ),
    types.FunctionDeclaration(
        name="create_booking",
        description=(
            "Chuẩn bị yêu cầu đặt một slot và trả về CONFIRMATION_REQUIRED. "
            "Công cụ này không tạo lịch hẹn; người dùng phải bấm nút xác nhận trên giao diện."
        ),
        parameters_json_schema=CreateBookingArgs.model_json_schema(),
    ),
    types.FunctionDeclaration(
        name="handoff_to_staff",
        description="Tạo yêu cầu chuyển cuộc trao đổi cho nhân viên khi người dùng cần hỗ trợ.",
        parameters_json_schema=HandoffToStaffArgs.model_json_schema(),
    ),
]

GEMINI_TOOL = types.Tool(function_declarations=TOOL_DECLARATIONS)

