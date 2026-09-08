from datetime import date,timedelta
import re
from tracemalloc import start
from typing import Optional
import mcp
from sqlalchemy import select, func
from model.database import AsyncSessionLocal
from model.employee import Employee
from model.attendance import Attendance


def register_analytics_tools(mcp):

    @mcp.tool()
    async def get_attendance_rate(
        start_date: date,
        end_date: date,
    )-> dict:

        if start_date > end_date:
            raise ValueError("Start date cannot be after end date.")
        async with AsyncSessionLocal() as db:
            active_result = await db.execute(
                select(func.count(Employee.id)).where(Employee.is_active.is_(True))
            )
            total_employees = active_result.scalar() or 0

            if total_employees == 0:
                return{
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                    "total_employees": 0,
                    "working_days": 0,
                    "expected_attendance": 0,
                    "present_days": 0,
                    "attendance_rate": 0.0,
                }
            total_days=(end_date - start_date).days + 1

            present_result= await db.execute(
                select(func.count(Attendance.id)).join(Employee,Employee.id==Attendance.employee_id).where(
                    Attendance.attendance_date.between(start_date,end_date),
                    Employee.is_active.is_(True),
                )
            )
            present_days=present_result.scalar() or 0
            expected_attendence=(
                total_employees * total_days
            )

            attendence_rate=(
                present_days / expected_attendence *100
                if expected_attendence
                else 0
            )

            return{
                "start_date": start_date.isoformat(),
                "end_date":end_date.isoformat(),
                "total_employees": total_employees,
                "days":total_days,
                "expected_attendence":expected_attendence,
                "present_days":present_days,
                "attendance_rate":round(
                    attendence_rate,
                    2,
                ),
            }
    @mcp.tool()
    async def get_frequent_absentees(
        start_date: date,
        end_date: date,
        minimum_absent_days: int = 1,
    ) -> list[dict]:
        """
        Find employees with frequent absences
        during a given date range.
        """

        if start_date > end_date:
            raise ValueError(
                "start_date cannot be after end_date."
            )

        if minimum_absent_days < 1:
            raise ValueError(
                "minimum_absent_days must be at least 1."
            )

        async with AsyncSessionLocal() as db:

            stmt = (
                select(
                    Employee.id,
                    Employee.name,
                    Employee.department,
                    func.count(Attendance.id).label(
                        "absent_days"
                    ),
                )
                .join(
                    Attendance,
                    Attendance.employee_id == Employee.id,
                )
                .where(
                    Attendance.attendance_date.between(
                        start_date,
                        end_date,
                    ),
                    Attendance.status.ilike("absent"),
                    Employee.is_active.is_(True),
                )
                .group_by(
                    Employee.id,
                    Employee.name,
                    Employee.department,
                )
                .having(
                    func.count(Attendance.id)
                    >= minimum_absent_days
                )
                .order_by(
                    func.count(Attendance.id).desc()
                )
            )

            result = await db.execute(stmt)

            rows = result.all()

            return [
                {
                    "employee_id": row.id,
                    "name": row.name,
                    "department": row.department,
                    "absent_days": row.absent_days,
                }
                for row in rows
            ]
    @mcp.tool()
    async def get_frequent_late_employees(
        start_date: date,
        end_date: date,
        minimum_late_days: int = 1,
    ) -> list[dict]:
        """
        Find employees who were late frequently
        during a given date range.
        """

        if start_date > end_date:
            raise ValueError(
                "start_date cannot be after end_date."
            )

        if minimum_late_days < 1:
            raise ValueError(
                "minimum_late_days must be at least 1."
            )

        async with AsyncSessionLocal() as db:

            stmt = (
                select(
                    Employee.id,
                    Employee.name,
                    Employee.department,
                    func.count(Attendance.id).label(
                        "late_days"
                    ),
                )
                .join(
                    Attendance,
                    Attendance.employee_id == Employee.id,
                )
                .where(
                    Attendance.attendance_date.between(
                        start_date,
                        end_date,
                    ),
                    Attendance.status.ilike("late"),
                    Employee.is_active.is_(True),
                )
                .group_by(
                    Employee.id,
                    Employee.name,
                    Employee.department,
                )
                .having(
                    func.count(Attendance.id)
                    >= minimum_late_days
                )
                .order_by(
                    func.count(Attendance.id).desc()
                )
            )

            result = await db.execute(stmt)

            rows = result.all()

            return [
                {
                    "employee_id": row.id,
                    "name": row.name,
                    "department": row.department,
                    "late_days": row.late_days,
                }
                for row in rows
            ]


    # ============================================================
    # TOOL 4: DEPARTMENT ATTENDANCE
    # ============================================================

    @mcp.tool()
    async def get_department_attendance(
        start_date: date,
        end_date: date,
    ) -> list[dict]:
        """
        Calculate attendance rate for each department.
        """

        if start_date > end_date:
            raise ValueError(
                "start_date cannot be after end_date."
            )

        total_days = (
            end_date - start_date
        ).days + 1

        async with AsyncSessionLocal() as db:

            employees_stmt = (
                select(
                    Employee.department,
                    func.count(Employee.id).label(
                        "employee_count"
                    ),
                )
                .where(
                    Employee.is_active.is_(True)
                )
                .group_by(Employee.department)
            )

            employee_result = await db.execute(
                employees_stmt
            )

            employee_rows = employee_result.all()

            attendance_stmt = (
                select(
                    Employee.department,
                    func.count(Attendance.id).label(
                        "present_days"
                    ),
                )
                .join(
                    Attendance,
                    Attendance.employee_id == Employee.id,
                )
                .where(
                    Attendance.attendance_date.between(
                        start_date,
                        end_date,
                    ),
                    Attendance.status.ilike("present"),
                    Employee.is_active.is_(True),
                )
                .group_by(Employee.department)
            )

            attendance_result = await db.execute(
                attendance_stmt
            )

            attendance_rows = attendance_result.all()

            attendance_map = {
                row.department: row.present_days
                for row in attendance_rows
            }

            output = []

            for row in employee_rows:

                department = row.department
                employee_count = row.employee_count

                expected = (
                    employee_count * total_days
                )

                present = attendance_map.get(
                    department,
                    0,
                )

                rate = (
                    present / expected * 100
                    if expected
                    else 0
                )

                output.append(
                    {
                        "department": department,
                        "employee_count": employee_count,
                        "present_days": present,
                        "expected_attendance": expected,
                        "attendance_rate": round(
                            rate,
                            2,
                        ),
                    }
                )

            output.sort(
                key=lambda x: x["attendance_rate"],
                reverse=True,
            )

            return output