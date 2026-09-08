from datetime import date, datetime

from sqlalchemy import select

from model.attendance import Attendance
from model.database import AsyncSessionLocal
from model.employee import Employee


def register_attendance_action_tools(mcp):

    # ============================================================
    # TOOL 1: MARK CHECK-IN
    # ============================================================

    @mcp.tool()
    async def mark_check_in(
        employee_id: int,
        check_in_time: datetime | None = None,
    ) -> dict:

        if check_in_time is None:
            check_in_time = datetime.now()

        attendance_date = check_in_time.date()

        async with AsyncSessionLocal() as db:

            employee_result = await db.execute(
                select(Employee).where(
                    Employee.id == employee_id
                )
            )

            employee = employee_result.scalar_one_or_none()

            if employee is None:
                raise ValueError(
                    f"Employee '{employee_id}' not found in the system."
                )

            if not employee.is_active:
                raise ValueError(
                    f"Employee '{employee.name}' is not active "
                    "and cannot mark attendance."
                )

            attendance_result = await db.execute(
                select(Attendance).where(
                    Attendance.employee_id == employee_id,
                    Attendance.attendance_date == attendance_date,
                )
            )

            attendance = attendance_result.scalar_one_or_none()

            if attendance and attendance.check_in:
                return {
                    "success": False,
                    "message": (
                        f"Employee '{employee.name}' has already "
                        f"checked in on {attendance_date}."
                    ),
                    "employee_id": employee.id,
                    "name": employee.name,
                    "attendance_date": attendance_date.isoformat(),
                    "check_in": attendance.check_in.isoformat(),
                    "status": attendance.status,
                }

            if attendance is None:
                attendance = Attendance(
                    employee_id=employee_id,
                    attendance_date=attendance_date,
                    check_in=check_in_time,
                    status="Present",
                )

                db.add(attendance)

            else:
                attendance.check_in = check_in_time
                attendance.status = "Present"

            await db.commit()
            await db.refresh(attendance)

            return {
                "success": True,
                "message": (
                    f"{employee.name} checked in successfully."
                ),
                "employee_id": employee.id,
                "name": employee.name,
                "attendance_date": attendance_date.isoformat(),
                "check_in": check_in_time.isoformat(),
                "status": attendance.status,
            }

    @mcp.tool()
    async def mark_check_out(
        employee_id: int,
        check_out_time: datetime | None = None,
    ) -> dict:

        if check_out_time is None:
            check_out_time = datetime.now()

        attendance_date = check_out_time.date()

        async with AsyncSessionLocal() as db:

            employee_result = await db.execute(
                select(Employee).where(
                    Employee.id == employee_id
                )
            )

            employee = employee_result.scalar_one_or_none()

            if employee is None:
                raise ValueError(
                    f"Employee '{employee_id}' not found in the system."
                )

            attendance_result = await db.execute(
                select(Attendance).where(
                    Attendance.employee_id == employee_id,
                    Attendance.attendance_date == attendance_date,
                )
            )

            attendance = attendance_result.scalar_one_or_none()

            if attendance is None:
                raise ValueError(
                    f"No check-in record found for "
                    f"employee '{employee.name}' on {attendance_date}."
                )

            if attendance.check_in is None:
                raise ValueError(
                    f"{employee.name} has not checked in yet."
                )

            if attendance.check_out is not None:
                return {
                    "success": False,
                    "message": (
                        f"{employee.name} has already checked out."
                    ),
                    "employee_id": employee.id,
                    "name": employee.name,
                    "attendance_date": attendance_date.isoformat(),
                    "check_in": attendance.check_in.isoformat(),
                    "check_out": attendance.check_out.isoformat(),
                }

            if check_out_time < attendance.check_in:
                raise ValueError(
                    "Check-out time cannot be earlier "
                    "than check-in time."
                )

            attendance.check_out = check_out_time

            await db.commit()
            await db.refresh(attendance)

            working_seconds = (
                attendance.check_out - attendance.check_in
            ).total_seconds()

            working_hours = round(
                working_seconds / 3600,
                2,
            )

            return {
                "success": True,
                "message": (
                    f"{employee.name} checked out successfully."
                ),
                "employee_id": employee.id,
                "name": employee.name,
                "attendance_date": attendance_date.isoformat(),
                "check_in": attendance.check_in.isoformat(),
                "check_out": attendance.check_out.isoformat(),
                "working_hours": working_hours,
            }

    @mcp.tool()
    async def calculate_working_hours(
        employee_id: int,
        attendance_date: date,
    ) -> dict:

        async with AsyncSessionLocal() as db:

            employee_result = await db.execute(
                select(Employee).where(
                    Employee.id == employee_id
                )
            )

            employee = employee_result.scalar_one_or_none()

            if employee is None:
                raise ValueError(
                    f"{employee_id} not found in the system."
                )

            attendance_result = await db.execute(
                select(Attendance).where(
                    Attendance.employee_id == employee_id,
                    Attendance.attendance_date == attendance_date,
                )
            )

            attendance = attendance_result.scalar_one_or_none()

            if attendance is None:
                return {
                    "employee_id": employee.id,
                    "name": employee.name,
                    "attendance_date": attendance_date.isoformat(),
                    "working_hours": 0.0,
                    "status": "Absent",
                    "message": (
                        "No attendance record found "
                        "for the specified date."
                    ),
                }

            if attendance.check_in is None:
                return {
                    "employee_id": employee.id,
                    "name": employee.name,
                    "attendance_date": attendance_date.isoformat(),
                    "working_hours": 0.0,
                    "status": "Absent",
                    "message": (
                        "Check-in time is missing "
                        "for the specified date."
                    ),
                }

            if attendance.check_out is None:
                return {
                    "employee_id": employee.id,
                    "name": employee.name,
                    "attendance_date": attendance_date.isoformat(),
                    "check_in": attendance.check_in.isoformat(),
                    "working_hours": None,
                    "status": attendance.status,
                    "message": (
                        "Employee has not checked out yet."
                    ),
                }

            working_seconds = (
                attendance.check_out - attendance.check_in
            ).total_seconds()

            working_hours = round(
                working_seconds / 3600,
                2,
            )

            return {
                "employee_id": employee.id,
                "name": employee.name,
                "attendance_date": attendance_date.isoformat(),
                "check_in": attendance.check_in.isoformat(),
                "check_out": attendance.check_out.isoformat(),
                "working_hours": working_hours,
                "status": attendance.status,
            }

    @mcp.tool()
    async def auto_mark_absent(
        attendance_date: date | None = None,
    ) -> dict:

        if attendance_date is None:
            attendance_date = date.today()

        async with AsyncSessionLocal() as db:

            employee_result = await db.execute(
                select(Employee).where(
                    Employee.is_active.is_(True)
                )
            )

            employees = employee_result.scalars().all()

            marked_absent = []

            for employee in employees:

                attendance_result = await db.execute(
                    select(Attendance).where(
                        Attendance.employee_id == employee.id,
                        Attendance.attendance_date == attendance_date,
                    )
                )

                attendance = (
                    attendance_result.scalar_one_or_none()
                )

                if attendance is None:

                    attendance = Attendance(
                        employee_id=employee.id,
                        attendance_date=attendance_date,
                        status="Absent",
                    )

                    db.add(attendance)

                    marked_absent.append(
                        {
                            "employee_id": employee.id,
                            "name": employee.name,
                            "department": employee.department,
                        }
                    )

            await db.commit()

            return {
                "success": True,
                "attendance_date": attendance_date.isoformat(),
                "absent_count": len(marked_absent),
                "employees": marked_absent,
            }