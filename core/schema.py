import graphene
import graphql_jwt
from django.utils import timezone
from graphql_jwt.shortcuts import get_token
from graphql_jwt.decorators import login_required
from graphene_django.types import DjangoObjectType
from graphene_file_upload.scalars import Upload
from datetime import datetime, date as date_type
from datetime import timedelta
from .models import (
    User, Employee,
    DayToDay, ProcessEntry,
    Attendance,
    DashboardTotal, DailyProduction, MonthlyProduction, YearlyProduction,
)
from .utils import update_dashboard_counters


# ═════════════════════════════════════════════════════════════
#  H E L P E R   P E R M I S S I O N   C H E C K S
# ═════════════════════════════════════════════════════════════

def require_active(info):
    """User must be logged in and active. Attendance screen access."""
    user = info.context.user
    if not user.is_authenticated:
        raise Exception("Authentication required. Please log in.")
    if not user.active:
        raise Exception("Your account is inactive. Contact admin.")


def require_admin(info):
    """User must be logged in, active, AND admin. Full access."""
    user = info.context.user
    if not user.is_authenticated:
        raise Exception("Authentication required. Please log in.")
    if not user.active:
        raise Exception("Your account is inactive. Contact admin.")
    if not user.admin:
        raise Exception("Admin access required for this action.")


# ═════════════════════════════════════════════════════════════
#  G R A P H E N E   T Y P E S
# ═════════════════════════════════════════════════════════════

class UserType(DjangoObjectType):
    class Meta:
        model = User
        fields = ("id", "username", "full_name", "admin", "active", "last_login_at")


class EmployeeType(DjangoObjectType):
    dropdown_label = graphene.String()
    employee_id = graphene.String()

    class Meta:
        model = Employee
        fields = (
            "id", "employee_id", "name", "process",
            "designation", "department", "phone",
            "is_active", "created_at",
        )

    def resolve_employee_id(self, info):
        return self.employee_id

    def resolve_dropdown_label(self, info):
        return f"{self.employee_id} - {self.name}"


class DayToDayType(DjangoObjectType):
    class Meta:
        model = DayToDay
        fields = (
            "id", "process", "count", "input_numbers",
            "submitted_by", "date", "day", "month", "year", "created_at",
        )


# ✅ UPDATED: added reference_numbers to exposed fields
class ProcessEntryType(DjangoObjectType):
    class Meta:
        model = ProcessEntry
        fields = (
            "id", "process", "employee", "employee_name", "employee_id_snapshot",
            "count", "pass_count", "fail_count",
            "reference_numbers",          # ✅ NEW
            "submitted_by", "date", "day", "month", "year", "created_at",
        )


class AttendanceType(DjangoObjectType):
    photo_display_url     = graphene.String()
    in_photo_display_url  = graphene.String()
    out_photo_display_url = graphene.String()

    class Meta:
        model = Attendance
        fields = (
            "id", "employee", "employee_name", "employee_id_snapshot",
            "photo_url", "in_photo_url", "out_photo_url",
            "latitude", "longitude", "accuracy", "address",
            "in_time", "out_time",
            "captured_at", "day", "month", "year",
            "status", "uploaded_by", "remarks", "created_at",
        )

    def resolve_photo_display_url(self, info):
        if self.photo:
            return info.context.build_absolute_uri(self.photo.url)
        return self.photo_url

    def resolve_in_photo_display_url(self, info):
        if self.in_photo:
            return info.context.build_absolute_uri(self.in_photo.url)
        return self.in_photo_url

    def resolve_out_photo_display_url(self, info):
        if self.out_photo:
            return info.context.build_absolute_uri(self.out_photo.url)
        return self.out_photo_url


class DashboardTotalType(DjangoObjectType):
    class Meta:
        model = DashboardTotal
        fields = (
            "id", "key",
            "total_welding", "total_ut", "total_forming",
            "total_sr", "total_final_ut", "last_updated",
        )


class DailyProductionType(DjangoObjectType):
    class Meta:
        model = DailyProduction
        fields = ("id", "day", "month", "year", "welding", "ut", "forming", "sr", "final_ut", "last_updated")


class MonthlyProductionType(DjangoObjectType):
    class Meta:
        model = MonthlyProduction
        fields = ("id", "month", "year", "welding", "ut", "forming", "sr", "final_ut", "last_updated")


class YearlyProductionType(DjangoObjectType):
    class Meta:
        model = YearlyProduction
        fields = ("id", "year", "welding", "ut", "forming", "sr", "final_ut", "last_updated")


# ═════════════════════════════════════════════════════════════
#  Q U E R I E S
# ═════════════════════════════════════════════════════════════

class Query(graphene.ObjectType):

    # ── Auth ─────────────────────────────────────────────────
    current_user = graphene.Field(UserType)

    def resolve_current_user(self, info):
        require_active(info)
        return info.context.user

    # ── Employees ─────────────────────────────────────────────
    all_employees        = graphene.List(EmployeeType)
    employee_by_id       = graphene.Field(EmployeeType, id=graphene.ID(required=True))
    employees_by_process = graphene.List(EmployeeType, process=graphene.String(required=True))

    def resolve_all_employees(self, info):
        require_admin(info)
        return Employee.objects.filter(is_active=True)

    def resolve_employee_by_id(self, info, id):
        require_admin(info)
        try:
            return Employee.objects.get(id=id)
        except Employee.DoesNotExist:
            raise Exception("Employee not found")

    def resolve_employees_by_process(self, info, process):
        require_active(info)
        return Employee.objects.filter(process=process, is_active=True)

    # ── Day-to-Day Monitoring ─────────────────────────────────
    all_day_to_day        = graphene.List(DayToDayType)
    day_to_day_by_date    = graphene.List(DayToDayType, day=graphene.Int(), month=graphene.Int(required=True), year=graphene.Int(required=True))
    day_to_day_by_process = graphene.List(DayToDayType, process=graphene.String(required=True))

    def resolve_all_day_to_day(self, info):
        require_admin(info)
        return DayToDay.objects.all().order_by("-created_at")

    def resolve_day_to_day_by_date(self, info, month, year, day=None):
        require_admin(info)
        qs = DayToDay.objects.filter(month=month, year=year)
        if day:
            qs = qs.filter(day=day)
        return qs.order_by("-created_at")

    def resolve_day_to_day_by_process(self, info, process):
        require_admin(info)
        return DayToDay.objects.filter(process=process).order_by("-created_at")

    # ── Process Entries ───────────────────────────────────────
    all_process_entries         = graphene.List(ProcessEntryType)
    process_entries_by_employee = graphene.List(ProcessEntryType, employee_id=graphene.ID(required=True))
    process_entries_by_process  = graphene.List(ProcessEntryType, process=graphene.String(required=True))
    process_entries_by_date     = graphene.List(ProcessEntryType, day=graphene.Int(), month=graphene.Int(required=True), year=graphene.Int(required=True))

    def resolve_all_process_entries(self, info):
        require_admin(info)
        return ProcessEntry.objects.all().order_by("-created_at")

    def resolve_process_entries_by_employee(self, info, employee_id):
        require_admin(info)
        return ProcessEntry.objects.filter(employee_id=employee_id).order_by("-created_at")

    def resolve_process_entries_by_process(self, info, process):
        require_admin(info)
        return ProcessEntry.objects.filter(process=process).order_by("-created_at")

    def resolve_process_entries_by_date(self, info, month, year, day=None):
        require_admin(info)
        qs = ProcessEntry.objects.filter(month=month, year=year)
        if day:
            qs = qs.filter(day=day)
        return qs.order_by("-created_at")

    # ── Attendance ────────────────────────────────────────────
    all_attendance         = graphene.List(AttendanceType)
    attendance_by_employee = graphene.List(AttendanceType, employee_id=graphene.ID(required=True))
    attendance_by_date     = graphene.List(AttendanceType, day=graphene.Int(), month=graphene.Int(required=True), year=graphene.Int(required=True))

    def resolve_all_attendance(self, info):
        require_active(info)
        return Attendance.objects.all().order_by("-captured_at")

    def resolve_attendance_by_employee(self, info, employee_id):
        require_active(info)
        return Attendance.objects.filter(employee_id=employee_id).order_by("-captured_at")

    def resolve_attendance_by_date(self, info, month, year, day=None):
        require_active(info)
        qs = Attendance.objects.filter(month=month, year=year)
        if day:
            qs = qs.filter(day=day)
        return qs.order_by("-captured_at")

    # ── Dashboard ─────────────────────────────────────────────
    dashboard_total    = graphene.Field(DashboardTotalType)
    daily_production   = graphene.List(DailyProductionType, month=graphene.Int(required=True), year=graphene.Int(required=True))
    monthly_production = graphene.List(MonthlyProductionType, year=graphene.Int(required=True))
    yearly_production  = graphene.List(YearlyProductionType)
    today_production   = graphene.Field(DailyProductionType)

    def resolve_dashboard_total(self, info):
        require_admin(info)
        obj, _ = DashboardTotal.objects.get_or_create(key="GLOBAL")
        return obj

    def resolve_daily_production(self, info, month, year):
        require_admin(info)
        return DailyProduction.objects.filter(month=month, year=year).order_by("day")

    def resolve_monthly_production(self, info, year):
        require_admin(info)
        return MonthlyProduction.objects.filter(year=year).order_by("month")

    def resolve_yearly_production(self, info):
        require_admin(info)
        return YearlyProduction.objects.all().order_by("year")

    def resolve_today_production(self, info):
        require_admin(info)
        today = date_type.today()
        try:
            return DailyProduction.objects.get(day=today.day, month=today.month, year=today.year)
        except DailyProduction.DoesNotExist:
            return None


# ═════════════════════════════════════════════════════════════
#  M U T A T I O N S
# ═════════════════════════════════════════════════════════════

# ── Auth ──────────────────────────────────────────────────────

class CreateUser(graphene.Mutation):
    user    = graphene.Field(UserType)
    token   = graphene.String()
    success = graphene.Boolean()
    message = graphene.String()

    class Arguments:
        username  = graphene.String(required=True)
        password  = graphene.String(required=True)
        full_name = graphene.String(required=False)
        is_admin  = graphene.Boolean(required=False, default_value=False)

    def mutate(self, info, username, password, full_name=None, is_admin=False):
        require_admin(info)
        if User.objects.filter(username=username).exists():
            return CreateUser(success=False, message="Username already taken")
        user = User.objects.create_user(username=username, password=password, is_admin=is_admin)
        if full_name:
            user.full_name = full_name
            user.save()
        token = get_token(user)
        return CreateUser(success=True, message="User created successfully", user=user, token=token)


class LoginUser(graphene.Mutation):
    token   = graphene.String()
    success = graphene.Boolean()
    message = graphene.String()
    user    = graphene.Field(UserType)

    class Arguments:
        username = graphene.String(required=True)
        password = graphene.String(required=True)

    def mutate(self, info, username, password):
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            return LoginUser(success=False, message="Invalid username or password", token=None, user=None)

        if not user.check_password(password):
            return LoginUser(success=False, message="Invalid username or password", token=None, user=None)

        if not user.active:
            return LoginUser(success=False, message="Account is disabled. Contact admin.", token=None, user=None)

        user.last_login_at = timezone.now()
        user.save(update_fields=["last_login_at"])

        token = get_token(user)
        return LoginUser(success=True, message="Login successful", token=token, user=user)


class ForgotPassword(graphene.Mutation):
    success     = graphene.Boolean()
    message     = graphene.String()
    reset_token = graphene.String()

    class Arguments:
        username = graphene.String(required=True)

    def mutate(self, info, username):
        import secrets
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            return ForgotPassword(success=False, message="Username not found", reset_token=None)

        token = secrets.token_urlsafe(32)
        user.reset_password_token   = token
        user.reset_password_expires = timezone.now() + timedelta(hours=1)
        user.save()

        return ForgotPassword(
            success=True,
            message="Reset token generated. Share with user securely.",
            reset_token=token,
        )


class ResetPassword(graphene.Mutation):
    success = graphene.Boolean()
    message = graphene.String()

    class Arguments:
        username     = graphene.String(required=True)
        reset_token  = graphene.String(required=True)
        new_password = graphene.String(required=True)

    def mutate(self, info, username, reset_token, new_password):
        try:
            user = User.objects.get(username=username, reset_password_token=reset_token)
        except User.DoesNotExist:
            return ResetPassword(success=False, message="Invalid token or username")

        if user.reset_password_expires and user.reset_password_expires < timezone.now():
            return ResetPassword(success=False, message="Token has expired")

        user.set_password(new_password)
        user.reset_password_token   = None
        user.reset_password_expires = None
        user.save()

        return ResetPassword(success=True, message="Password reset successfully")


# ── Employee ──────────────────────────────────────────────────

class CreateEmployee(graphene.Mutation):
    employee = graphene.Field(EmployeeType)
    success  = graphene.Boolean()
    message  = graphene.String()

    class Arguments:
        employee_id = graphene.String(required=True)
        name        = graphene.String(required=True)
        process     = graphene.String(required=True)
        designation = graphene.String(required=False)
        department  = graphene.String(required=False)
        phone       = graphene.String(required=False)

    def mutate(self, info, employee_id, name, process, designation=None, department=None, phone=None):
        require_admin(info)
        if Employee.objects.filter(employee_id=employee_id).exists():
            return CreateEmployee(success=False, message="Employee ID already exists")

        valid_processes = ["Welding", "UT", "Forming", "SR", "Final UT"]
        if process not in valid_processes:
            return CreateEmployee(success=False, message=f"Invalid process. Choose from: {valid_processes}")

        emp = Employee.objects.create(
            employee_id=employee_id,
            name=name,
            process=process,
            designation=designation,
            department=department,
            phone=phone,
        )
        return CreateEmployee(success=True, message="Employee created successfully", employee=emp)


class UpdateEmployee(graphene.Mutation):
    employee = graphene.Field(EmployeeType)
    success  = graphene.Boolean()
    message  = graphene.String()

    class Arguments:
        id          = graphene.ID(required=True)
        name        = graphene.String(required=False)
        process     = graphene.String(required=False)
        designation = graphene.String(required=False)
        department  = graphene.String(required=False)
        phone       = graphene.String(required=False)
        is_active   = graphene.Boolean(required=False)

    def mutate(self, info, id, name=None, process=None, designation=None, department=None, phone=None, is_active=None):
        require_admin(info)
        try:
            emp = Employee.objects.get(id=id)
        except Employee.DoesNotExist:
            return UpdateEmployee(success=False, message="Employee not found")

        if name:        emp.name        = name
        if process:     emp.process     = process
        if designation: emp.designation = designation
        if department:  emp.department  = department
        if phone:       emp.phone       = phone
        if is_active is not None: emp.is_active = is_active
        emp.save()

        return UpdateEmployee(success=True, message="Employee updated successfully", employee=emp)


class DeleteEmployee(graphene.Mutation):
    success = graphene.Boolean()
    message = graphene.String()

    class Arguments:
        id = graphene.ID(required=True)

    def mutate(self, info, id):
        require_admin(info)
        try:
            emp = Employee.objects.get(id=id)
        except Employee.DoesNotExist:
            return DeleteEmployee(success=False, message="Employee not found")
        emp.delete()
        return DeleteEmployee(success=True, message="Employee deleted successfully")


# ── Day-to-Day Monitoring ─────────────────────────────────────

class AddDayToDayEntry(graphene.Mutation):
    entry   = graphene.Field(DayToDayType)
    success = graphene.Boolean()
    message = graphene.String()

    class Arguments:
        process       = graphene.String(required=True)
        count         = graphene.Int(required=True)
        input_numbers = graphene.String(required=False)

    def mutate(self, info, process, count, input_numbers=None):
        require_admin(info)

        valid_processes = ["Welding", "UT", "Forming", "SR"]
        if process not in valid_processes:
            return AddDayToDayEntry(success=False, message=f"Invalid process. Choose: {valid_processes}")

        if not (1 <= count <= 20):
            return AddDayToDayEntry(success=False, message="Count must be between 1 and 20")

        today = date_type.today()
        entry = DayToDay.objects.create(
            process=process,
            count=count,
            input_numbers=input_numbers,
            submitted_by=info.context.user,
            date=today,
            day=today.day,
            month=today.month,
            year=today.year,
        )

        update_dashboard_counters(process, count, today)

        return AddDayToDayEntry(success=True, message="Entry recorded and dashboard updated", entry=entry)


# ── Process Screen ────────────────────────────────────────────

class AddProcessEntry(graphene.Mutation):
    entry   = graphene.Field(ProcessEntryType)
    success = graphene.Boolean()
    message = graphene.String()

    class Arguments:
        process           = graphene.String(required=True)
        employee_id       = graphene.ID(required=True)
        count             = graphene.Int(required=True)
        pass_count        = graphene.Int(required=False)
        fail_count        = graphene.Int(required=False)
        reference_numbers = graphene.String(required=False)   # ✅ NEW — comma-separated e.g. "101,102,103"

    def mutate(self, info, process, employee_id, count,
               pass_count=0, fail_count=0, reference_numbers=None):
        require_admin(info)

        valid_processes = ["Welding", "UT", "Forming", "SR", "Final UT"]
        if process not in valid_processes:
            return AddProcessEntry(success=False, message=f"Invalid process. Choose: {valid_processes}")

        if not (1 <= count <= 20):
            return AddProcessEntry(success=False, message="Count must be between 1 and 20")

        try:
            emp = Employee.objects.get(id=employee_id, is_active=True)
        except Employee.DoesNotExist:
            return AddProcessEntry(success=False, message="Employee not found")

        # ── Duplicate reference number check (across ALL existing entries) ──
        if reference_numbers:
            incoming = [r.strip() for r in reference_numbers.split(',') if r.strip()]

            # Collect every reference number already stored in the DB
            existing_refs = set()
            for entry in ProcessEntry.objects.exclude(reference_numbers='').values_list('reference_numbers', flat=True):
                for ref in entry.split(','):
                    existing_refs.add(ref.strip())

            duplicates = [r for r in incoming if r in existing_refs]
            if duplicates:
                return AddProcessEntry(
                    success=False,
                    message=f"Duplicate reference numbers already submitted: {', '.join(duplicates)}"
                )

        today = date_type.today()
        entry = ProcessEntry.objects.create(
            process=process,
            employee=emp,
            employee_name=emp.name,
            employee_id_snapshot=emp.employee_id,
            count=count,
            pass_count=pass_count,
            fail_count=fail_count,
            reference_numbers=reference_numbers or '',   # ✅ save to DB
            submitted_by=info.context.user,
            date=today,
            day=today.day,
            month=today.month,
            year=today.year,
        )

        update_dashboard_counters(process, count, today)

        return AddProcessEntry(
            success=True,
            message="Process entry submitted and dashboard updated",
            entry=entry,
        )


# ── Attendance ────────────────────────────────────────────────

class UploadAttendance(graphene.Mutation):
    attendance = graphene.Field(AttendanceType)
    success    = graphene.Boolean()
    message    = graphene.String()

    class Arguments:
        employee_id = graphene.ID(required=True)
        photo       = Upload(required=False)
        photo_url   = graphene.String(required=False)
        latitude    = graphene.Float(required=True)
        longitude   = graphene.Float(required=True)
        accuracy    = graphene.Float(required=False)
        address     = graphene.String(required=False)
        captured_at = graphene.String(required=True)
        status      = graphene.String(required=False, default_value="Present")
        remarks     = graphene.String(required=False)

    def mutate(
        self, info, employee_id, latitude, longitude, captured_at,
        photo=None, photo_url=None, accuracy=None, address=None,
        status="Present", remarks=None
    ):
        require_active(info)

        try:
            emp = Employee.objects.get(id=employee_id, is_active=True)
        except Employee.DoesNotExist:
            return UploadAttendance(success=False, message="Employee not found")

        if not photo and not photo_url:
            return UploadAttendance(success=False, message="Either a photo file or photo_url is required")

        try:
            captured_dt = datetime.fromisoformat(captured_at)
        except ValueError:
            return UploadAttendance(success=False, message="Invalid captured_at format. Use ISO 8601.")

        valid_statuses = ["Present", "Late", "Half Day", "Absent"]
        if status not in valid_statuses:
            return UploadAttendance(success=False, message=f"Invalid status. Choose: {valid_statuses}")

        if Attendance.objects.filter(
            employee=emp,
            day=captured_dt.day,
            month=captured_dt.month,
            year=captured_dt.year,
        ).exists():
            return UploadAttendance(
                success=False,
                message=f"Attendance already recorded for {emp.name} on {captured_dt.date()}"
            )

        att = Attendance.objects.create(
            employee=emp,
            employee_name=emp.name,
            employee_id_snapshot=emp.employee_id,
            photo=photo,
            photo_url=photo_url,
            latitude=latitude,
            longitude=longitude,
            accuracy=accuracy,
            address=address,
            in_time=captured_dt,
            captured_at=captured_dt,
            day=captured_dt.day,
            month=captured_dt.month,
            year=captured_dt.year,
            status=status,
            uploaded_by=info.context.user,
            remarks=remarks,
        )
        return UploadAttendance(success=True, message="Attendance uploaded successfully", attendance=att)


class ClockOut(graphene.Mutation):
    attendance = graphene.Field(AttendanceType)
    success    = graphene.Boolean()
    message    = graphene.String()

    class Arguments:
        employee_id = graphene.ID(required=True)
        photo_url   = graphene.String(required=False)
        captured_at = graphene.String(required=True)

    def mutate(self, info, employee_id, captured_at, photo_url=None):
        require_active(info)

        try:
            emp = Employee.objects.get(id=employee_id, is_active=True)
        except Employee.DoesNotExist:
            return ClockOut(success=False, message="Employee not found")

        try:
            out_dt = datetime.fromisoformat(captured_at)
        except ValueError:
            return ClockOut(success=False, message="Invalid captured_at format")

        try:
            att = Attendance.objects.get(
                employee=emp,
                day=out_dt.day,
                month=out_dt.month,
                year=out_dt.year,
            )
        except Attendance.DoesNotExist:
            return ClockOut(success=False, message="No clock-in found for today. Please clock in first.")

        if att.out_time:
            return ClockOut(success=False, message="Already clocked out today.")

        att.out_time = out_dt
        if photo_url:
            att.out_photo_url = photo_url
        att.save()

        return ClockOut(success=True, message="Clocked out successfully", attendance=att)


# ═════════════════════════════════════════════════════════════
#  M U T A T I O N   R O O T
# ═════════════════════════════════════════════════════════════

class Mutation(graphene.ObjectType):

    # Auth (open — no login needed)
    login_user      = LoginUser.Field()
    forgot_password = ForgotPassword.Field()
    reset_password  = ResetPassword.Field()

    # Auth (admin only)
    create_user   = CreateUser.Field()

    # Standard JWT helpers
    token_auth    = graphql_jwt.ObtainJSONWebToken.Field()
    verify_token  = graphql_jwt.Verify.Field()
    refresh_token = graphql_jwt.Refresh.Field()

    # Employee (admin only)
    create_employee = CreateEmployee.Field()
    update_employee = UpdateEmployee.Field()
    delete_employee = DeleteEmployee.Field()

    # Day-to-Day Monitoring screen (admin only)
    add_day_to_day_entry = AddDayToDayEntry.Field()

    # Process screen (admin only)
    add_process_entry = AddProcessEntry.Field()

    # Attendance screen (active users — admin or not)
    upload_attendance = UploadAttendance.Field()
    clock_out         = ClockOut.Field()


# ═════════════════════════════════════════════════════════════
#  S C H E M A
# ═════════════════════════════════════════════════════════════

schema = graphene.Schema(query=Query, mutation=Mutation)