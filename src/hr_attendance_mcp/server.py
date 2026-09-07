import re

from mcp.server.mcpserver import MCPServer

from hr_attendance_mcp.tools.attendance import (
    register_attendance_tools,
)
from hr_attendance_mcp.tools.employee import (
    register_employee_tools,
)
from hr_attendance_mcp.tools.analytics import (
    register_analytics_tools,
)


# ============================================================
# MCP SERVER
# ============================================================

mcp = MCPServer(
    name="HR Attendance Assistant",
    description="MCP server for HR employee attendance management.",
)


# ============================================================
# REGISTER TOOLS
# ============================================================

register_attendance_tools(mcp)
register_employee_tools(mcp)
register_analytics_tools(mcp)



if __name__ == "__main__":
    mcp.run()