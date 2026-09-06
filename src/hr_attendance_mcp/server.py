from datetime import date, datetime
from typing import Optional

from sqlalchemy import func, select

from mcp.server.mcpserver import MCPServer

from model.attendance import Attendance
from model.database import AsyncSessionLocal
from model.employee import Employee


# ============================================================
# MCP SERVER
# ============================================================

mcp = MCPServer(
    name="HR Attendance Assistant",
    description="MCP server for HR employee attendance management.",
)


# ============================================================
# HELPER
# ============================================================

def parse_date(value: str) -> date:
    """
    Convert YYYY-MM-DD string to Python date.
    """
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise ValueError(
            f"Invalid date format: {value}. "
            "Use YYYY-MM-DD."
        )


# ============================================================
# TOOL 1: TODAY'S ATTENDANCE
# ============================================================

@mcp.tool()
async def get_today_attendance() -> list[dict]:
    """
    Get today's attendance information for all employees.
    """

    today = date.today()

    async with AsyncSessionLocal() as db:

        result = await db.execute(
            select(
                Employee.id,
                Employee.name,
                Employee.email,
                Employee.department,
                Attendance.attendance_date,
                Attendance.check_in,
                Attendance.check_out,
                Attendance.status,
            )
            .outerjoin(
                Attendance,
                (Employee.id == Attendance.employee_id)
                & (Attendance.attendance_date == today),
            )
            .where(Employee.is_active.is_(True))
            .order_by(Employee.id)
        )

        rows = result.all()

        return [
            {
                "employee_id": row.id,
                "name": row.name,
                "email": row.email,
                "department": row.department,
                "date": (
                    row.attendance_date.isoformat()
                    if row.attendance_date
                    else today.isoformat()
                ),
                "check_in": (
                    row.check_in.isoformat()
                    if row.check_in
                    else None
                ),
                "check_out": (
                    row.check_out.isoformat()
                    if row.check_out
                    else None
                ),
                "status": row.status or "not_marked",
            }
            for row in rows
        ]


# ============================================================
# TOOL 2: ABSENT EMPLOYEES
# ============================================================

@mcp.tool()
async def get_absent_employees(
    attendance_date: Optional[str] = None,
) -> list[dict]:
    """
    Get employees who are absent on a specific date.

    If no date is provided, today's date is used.
    """

    target_date = (
        parse_date(attendance_date)
        if attendance_date
        else date.today()
    )

    async with AsyncSessionLocal() as db:

        result = await db.execute(
            select(
                Employee.id,
                Employee.name,
                Employee.email,
                Employee.department,
                Attendance.status,
            )
            .outerjoin(
                Attendance,
                (Employee.id == Attendance.employee_id)
                & (Attendance.attendance_date == target_date),
            )
            .where(
                Employee.is_active.is_(True),
                (
                    Attendance.id.is_(None)
                    | (Attendance.status == "absent")
                ),
            )
            .order_by(Employee.id)
        )

        rows = result.all()

        return [
            {
                "employee_id": row.id,
                "name": row.name,
                "email": row.email,
                "department": row.department,
                "date": target_date.isoformat(),
                "status": "absent",
            }
            for row in rows
        ]


# ============================================================
# TOOL 3: LATE EMPLOYEES
# ============================================================

@mcp.tool()
async def get_late_employees(
    attendance_date: Optional[str] = None,
) -> list[dict]:
    """
    Get employees marked as late on a specific date.

    If no date is provided, today's date is used.
    """

    target_date = (
        parse_date(attendance_date)
        if attendance_date
        else date.today()
    )

    async with AsyncSessionLocal() as db:

        result = await db.execute(
            select(
                Employee.id,
                Employee.name,
                Employee.email,
                Employee.department,
                Attendance.check_in,
                Attendance.status,
            )
            .join(
                Attendance,
                Employee.id == Attendance.employee_id,
            )
            .where(
                Employee.is_active.is_(True),
                Attendance.attendance_date == target_date,
                Attendance.status == "late",
            )
            .order_by(Employee.id)
        )

        rows = result.all()

        return [
            {
                "employee_id": row.id,
                "name": row.name,
                "email": row.email,
                "department": row.department,
                "date": target_date.isoformat(),
                "check_in": (
                    row.check_in.isoformat()
                    if row.check_in
                    else None
                ),
                "status": row.status,
            }
            for row in rows
        ]


# ============================================================
# TOOL 4: EMPLOYEE ATTENDANCE
# ============================================================

@mcp.tool()
async def get_employee_attendance(
    employee_id: int,
    start_date: str,
    end_date: str,
) -> list[dict]:
    """
    Get attendance records for one employee
    between start_date and end_date.

    Dates must use YYYY-MM-DD format.
    """

    start = parse_date(start_date)
    end = parse_date(end_date)

    if start > end:
        raise ValueError(
            "start_date cannot be greater than end_date."
        )

    async with AsyncSessionLocal() as db:

        employee_result = await db.execute(
            select(Employee).where(
                Employee.id == employee_id
            )
        )

        employee = employee_result.scalar_one_or_none()

        if employee is None:
            raise ValueError(
                f"Employee with ID {employee_id} not found."
            )

        result = await db.execute(
            select(Attendance)
            .where(
                Attendance.employee_id == employee_id,
                Attendance.attendance_date >= start,
                Attendance.attendance_date <= end,
            )
            .order_by(Attendance.attendance_date)
        )

        records = result.scalars().all()

        return [
            {
                "employee_id": employee.id,
                "employee_name": employee.name,
                "date": record.attendance_date.isoformat(),
                "check_in": (
                    record.check_in.isoformat()
                    if record.check_in
                    else None
                ),
                "check_out": (
                    record.check_out.isoformat()
                    if record.check_out
                    else None
                ),
                "status": record.status,
            }
            for record in records
        ]


# ============================================================
# TOOL 5: ATTENDANCE SUMMARY
# ============================================================

@mcp.tool()
async def get_attendance_summary(
    start_date: str,
    end_date: str,
) -> dict:
    """
    Get attendance statistics between two dates.

    Returns total records and counts for
    present, late, absent and other statuses.
    """

    start = parse_date(start_date)
    end = parse_date(end_date)

    if start > end:
        raise ValueError(
            "start_date cannot be greater than end_date."
        )

    async with AsyncSessionLocal() as db:

        result = await db.execute(
            select(
                Attendance.status,
                func.count(Attendance.id),
            )
            .where(
                Attendance.attendance_date >= start,
                Attendance.attendance_date <= end,
            )
            .group_by(Attendance.status)
        )

        rows = result.all()

        summary = {
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "total_records": 0,
            "present": 0,
            "late": 0,
            "absent": 0,
        }

        for status, count in rows:

            count = int(count)

            summary["total_records"] += count

            if status == "present":
                summary["present"] += count

            elif status == "late":
                summary["late"] += count

            elif status == "absent":
                summary["absent"] += count

        summary["other"] = (
            summary["total_records"]
            - summary["present"]
            - summary["late"]
            - summary["absent"]
        )

        return summary


# ============================================================
# START MCP SERVER
# ============================================================

if __name__ == "__main__":
    mcp.run()