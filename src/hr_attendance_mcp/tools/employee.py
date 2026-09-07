from typing import Optional

from sqlalchemy import or_, select

from model.database import AsyncSessionLocal
from model.employee import Employee


def register_employee_tools(mcp):

    # ============================================================
    # TOOL 1: SEARCH EMPLOYEE
    # ============================================================

    @mcp.tool()
    async def search_employee(
        query: Optional[str] = None,
        department: Optional[str] = None,
        active_only: bool = True,
    ) -> list[dict]:

        async with AsyncSessionLocal() as db:

            stmt = select(Employee)

            # Only active employees
            if active_only:
                stmt = stmt.where(
                    Employee.is_active.is_(True)
                )

            # Search by name or email
            if query:
                search_value = f"%{query.strip()}%"

                stmt = stmt.where(
                    or_(
                        Employee.name.ilike(search_value),
                        Employee.email.ilike(search_value),
                    )
                )

            # Filter by department
            if department:
                stmt = stmt.where(
                    Employee.department.ilike(
                        f"%{department.strip()}%"
                    )
                )

            stmt = stmt.order_by(Employee.id)

            result = await db.execute(stmt)

            employees = result.scalars().all()

            return [
                {
                    "id": employee.id,
                    "name": employee.name,
                    "email": employee.email,
                    "department": employee.department,
                    "is_active": employee.is_active,
                }
                for employee in employees
            ]


    # ============================================================
    # TOOL 2: GET EMPLOYEE PROFILE
    # ============================================================

    @mcp.tool()
    async def get_employee_profile(
        employee_id: int,
    ) -> dict:

        async with AsyncSessionLocal() as db:

            result = await db.execute(
                select(Employee).where(
                    Employee.id == employee_id
                )
            )

            employee = result.scalar_one_or_none()

            if employee is None:
                raise ValueError(
                    f"Employee with ID {employee_id} not found."
                )

            return {
                "id": employee.id,
                "name": employee.name,
                "email": employee.email,
                "department": employee.department,
                "is_active": employee.is_active,
            }


    # ============================================================
    # TOOL 3: GET ALL EMPLOYEES
    # ============================================================

    @mcp.tool()
    async def get_all_employees(
        active_only: bool = True,
    ) -> list[dict]:

        async with AsyncSessionLocal() as db:

            stmt = select(Employee)

            if active_only:
                stmt = stmt.where(
                    Employee.is_active.is_(True)
                )

            stmt = stmt.order_by(Employee.id)

            result = await db.execute(stmt)

            employees = result.scalars().all()

            return [
                {
                    "id": employee.id,
                    "name": employee.name,
                    "email": employee.email,
                    "department": employee.department,
                    "is_active": employee.is_active,
                }
                for employee in employees
            ]


    # ============================================================
    # TOOL 4: GET EMPLOYEES BY DEPARTMENT
    # ============================================================

    @mcp.tool()
    async def get_employees_by_department(
        department: str,
        active_only: bool = True,
    ) -> list[dict]:

        department = department.strip()

        if not department:
            raise ValueError(
                "Department name cannot be empty."
            )

        async with AsyncSessionLocal() as db:

            stmt = select(Employee).where(
                Employee.department.ilike(
                    f"%{department}%"
                )
            )

            if active_only:
                stmt = stmt.where(
                    Employee.is_active.is_(True)
                )

            stmt = stmt.order_by(Employee.name)

            result = await db.execute(stmt)

            employees = result.scalars().all()

            return [
                {
                    "id": employee.id,
                    "name": employee.name,
                    "email": employee.email,
                    "department": employee.department,
                    "is_active": employee.is_active,
                }
                for employee in employees
            ]


    # ============================================================
    # TOOL 5: GET EMPLOYEE COUNT
    # ============================================================

    @mcp.tool()
    async def get_employee_count() -> dict:
        async with AsyncSessionLocal() as db:

            result = await db.execute(
                select(Employee)
            )

            employees = result.scalars().all()

            total = len(employees)

            active = sum(
                1
                for employee in employees
                if employee.is_active
            )

            inactive = total - active

            return {
                "total_employees": total,
                "active_employees": active,
                "inactive_employees": inactive,
            }