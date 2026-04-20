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


class ProcessEntryType(DjangoObjectType):
    class Meta:
        model = ProcessEntry
        fields = (
            "id", "process", "employee", "employee_name", "employee_id_snapshot",
            "count", "pass_count",   # ✅ ADD
            "fail_count", "submitted_by", "date", "day", "month", "year", "created_at",
        )


class AttendanceType(DjangoObjectType):
    photo_display_url = graphene.String()

    class Meta:
        model = Attendance
        fields = (
            "id", "employee", "employee_name", "employee_id_snapshot",
            "photo_url", "latitude", "longitude", "accuracy", "address",
            "captured_at", "day", "month", "year",
            "status", "uploaded_by", "remarks", "created_at",
        )

    def resolve_photo_display_url(self, info):
        """Returns absolute URL if photo is stored locally."""
        if self.photo:
            request = info.context
            return request.build_absolute_uri(self.photo.url)
        return self.photo_url


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

    @login_required
    def resolve_current_user(self, info):
        return info.context.user

    # ── Employees ─────────────────────────────────────────────
    all_employees      = graphene.List(EmployeeType)
    employee_by_id     = graphene.Field(EmployeeType, id=graphene.ID(required=True))
    employees_by_process = graphene.List(EmployeeType, process=graphene.String(required=True))

    @login_required
    def resolve_all_employees(self, info):
        return Employee.objects.filter(is_active=True)

    @login_required
    def resolve_employee_by_id(self, info, id):
        try:
            return Employee.objects.get(id=id)
        except Employee.DoesNotExist:
            raise Exception("Employee not found")

  
    def resolve_employees_by_process(self, info, process):
        return Employee.objects.filter(process=process, is_active=True)

    # ── Day-to-Day Monitoring ─────────────────────────────────
    all_day_to_day      = graphene.List(DayToDayType)
    day_to_day_by_date  = graphene.List(DayToDayType, day=graphene.Int(), month=graphene.Int(required=True), year=graphene.Int(required=True))
    day_to_day_by_process = graphene.List(DayToDayType, process=graphene.String(required=True))

    @login_required
    def resolve_all_day_to_day(self, info):
        return DayToDay.objects.all().order_by("-created_at")

    @login_required
    def resolve_day_to_day_by_date(self, info, month, year, day=None):
        qs = DayToDay.objects.filter(month=month, year=year)
        if day:
            qs = qs.filter(day=day)
        return qs.order_by("-created_at")

    @login_required
    def resolve_day_to_day_by_process(self, info, process):
        return DayToDay.objects.filter(process=process).order_by("-created_at")

    # ── Process Entries ───────────────────────────────────────
    all_process_entries        = graphene.List(ProcessEntryType)
    process_entries_by_employee = graphene.List(ProcessEntryType, employee_id=graphene.ID(required=True))
    process_entries_by_process  = graphene.List(ProcessEntryType, process=graphene.String(required=True))
    process_entries_by_date     = graphene.List(ProcessEntryType, day=graphene.Int(), month=graphene.Int(required=True), year=graphene.Int(required=True))

    @login_required
    def resolve_all_process_entries(self, info):
        return ProcessEntry.objects.all().order_by("-created_at")

    @login_required
    def resolve_process_entries_by_employee(self, info, employee_id):
        return ProcessEntry.objects.filter(employee_id=employee_id).order_by("-created_at")

    @login_required
    def resolve_process_entries_by_process(self, info, process):
        return ProcessEntry.objects.filter(process=process).order_by("-created_at")

    @login_required
    def resolve_process_entries_by_date(self, info, month, year, day=None):
        qs = ProcessEntry.objects.filter(month=month, year=year)
        if day:
            qs = qs.filter(day=day)
        return qs.order_by("-created_at")

    # ── Attendance ────────────────────────────────────────────
    all_attendance           = graphene.List(AttendanceType)
    attendance_by_employee   = graphene.List(AttendanceType, employee_id=graphene.ID(required=True))
    attendance_by_date       = graphene.List(AttendanceType, day=graphene.Int(), month=graphene.Int(required=True), year=graphene.Int(required=True))

    @login_required
    def resolve_all_attendance(self, info):
        return Attendance.objects.all().order_by("-captured_at")

    @login_required
    def resolve_attendance_by_employee(self, info, employee_id):
        return Attendance.objects.filter(employee_id=employee_id).order_by("-captured_at")

    @login_required
    def resolve_attendance_by_date(self, info, month, year, day=None):
        qs = Attendance.objects.filter(month=month, year=year)
        if day:
            qs = qs.filter(day=day)
        return qs.order_by("-captured_at")

    # ── Dashboard ─────────────────────────────────────────────
    dashboard_total   = graphene.Field(DashboardTotalType)
    daily_production  = graphene.List(DailyProductionType, month=graphene.Int(required=True), year=graphene.Int(required=True))
    monthly_production = graphene.List(MonthlyProductionType, year=graphene.Int(required=True))
    yearly_production  = graphene.List(YearlyProductionType)
    today_production   = graphene.Field(DailyProductionType)

    @login_required
    def resolve_dashboard_total(self, info):
        obj, _ = DashboardTotal.objects.get_or_create(key="GLOBAL")
        return obj

    @login_required
    def resolve_daily_production(self, info, month, year):
        return DailyProduction.objects.filter(month=month, year=year).order_by("day")

    @login_required
    def resolve_monthly_production(self, info, year):
        return MonthlyProduction.objects.filter(year=year).order_by("month")

    @login_required
    def resolve_yearly_production(self, info):
        return YearlyProduction.objects.all().order_by("year")

    @login_required
    def resolve_today_production(self, info):
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
    """Register a new user (admin account creation)."""
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
        if User.objects.filter(username=username).exists():
            return CreateUser(success=False, message="Username already taken")

        user = User.objects.create_user(username=username, password=password, is_admin=is_admin)
        if full_name:
            user.full_name = full_name
            user.save()

        token = get_token(user)
        return CreateUser(success=True, message="User created successfully", user=user, token=token)


class LoginUser(graphene.Mutation):
    """Authenticate and return JWT token."""
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
            return LoginUser(success=False, message="Account is disabled", token=None, user=None)

        # Update last login
        user.last_login_at = timezone.now()
        user.save(update_fields=["last_login_at"])

        token = get_token(user)
        return LoginUser(success=True, message="Login successful", token=token, user=user)


class ForgotPassword(graphene.Mutation):
    """Generate a reset token (send via SMS/email in production)."""
    success = graphene.Boolean()
    message = graphene.String()
    reset_token = graphene.String()  # Return to frontend; in prod, send via SMS

    class Arguments:
        username = graphene.String(required=True)

    def mutate(self, info, username):
        import secrets
        from datetime import timedelta

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
    """Reset password using the token from ForgotPassword."""
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

    @login_required
    def mutate(self, info, employee_id, name, process, designation=None, department=None, phone=None):
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

    @login_required
    def mutate(self, info, id, name=None, process=None, designation=None, department=None, phone=None, is_active=None):
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

    @login_required
    def mutate(self, info, id):
        try:
            emp = Employee.objects.get(id=id)
        except Employee.DoesNotExist:
            return DeleteEmployee(success=False, message="Employee not found")
        emp.delete()
        return DeleteEmployee(success=True, message="Employee deleted successfully")


# ── Day-to-Day Monitoring ─────────────────────────────────────

class AddDayToDayEntry(graphene.Mutation):
    """
    Called when the user presses 'Update' on the Day-to-Day Monitoring screen.
    Saves the entry AND increments all dashboard counters.
    """
    entry   = graphene.Field(DayToDayType)
    success = graphene.Boolean()
    message = graphene.String()

    class Arguments:
        process       = graphene.String(required=True)   # Welding / UT / Forming / SR
        count         = graphene.Int(required=True)       # 1–20 dropdown
        input_numbers = graphene.String(required=False)   # free-text field

    @login_required
    def mutate(self, info, process, count, input_numbers=None):
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

        # ✅ Increment dashboard counters
        update_dashboard_counters(process, count, today)

        return AddDayToDayEntry(success=True, message="Entry recorded and dashboard updated", entry=entry)


# ── Process Screen ────────────────────────────────────────────

class AddProcessEntry(graphene.Mutation):
    """
    Called when the user presses 'Submit' on the Process screen.
    Saves worker-wise production AND increments all dashboard counters.
    """
    
    entry   = graphene.Field(ProcessEntryType)
    success = graphene.Boolean()
    message = graphene.String()

    class Arguments:
        process     = graphene.String(required=True)   # Welding/UT/Forming/SR/Final UT
        employee_id = graphene.ID(required=True)        # Employee DB id
        count       = graphene.Int(required=True)  
        pass_count  = graphene.Int(required=False)
        fail_count  = graphene.Int(required=False)     # 1–20 dropdown

    @login_required
    def mutate(self, info, process, employee_id, count, pass_count=0, fail_count=0):
        valid_processes = ["Welding", "UT", "Forming", "SR", "Final UT"]
        if process not in valid_processes:
            return AddProcessEntry(success=False, message=f"Invalid process. Choose: {valid_processes}")

        if not (1 <= count <= 20):
            return AddProcessEntry(success=False, message="Count must be between 1 and 20")

        try:
            emp = Employee.objects.get(id=employee_id, is_active=True)
        except Employee.DoesNotExist:
            return AddProcessEntry(success=False, message="Employee not found")

        today = date_type.today()
        entry = ProcessEntry.objects.create(
            process=process,
            employee=emp,
            employee_name=emp.name,
            employee_id_snapshot=emp.employee_id,
            count=count,
            pass_count=pass_count,     # ✅ ADD THIS
            fail_count=fail_count,  
            submitted_by=info.context.user,
            date=today,
            day=today.day,
            month=today.month,
            year=today.year,
        )

        # ✅ Increment dashboard counters
        update_dashboard_counters(process, count, today)

        return AddProcessEntry(success=True, message="Process entry submitted and dashboard updated", entry=entry)


# ── Attendance ────────────────────────────────────────────────

class UploadAttendance(graphene.Mutation):
    """
    Called when the user presses 'Upload' on the Attendance screen.
    Stores geo-tagged photo attendance record.
    """
    attendance = graphene.Field(AttendanceType)
    success    = graphene.Boolean()
    message    = graphene.String()

    class Arguments:
        employee_id  = graphene.ID(required=True)
        photo        = Upload(required=False)        # local file upload
        photo_url    = graphene.String(required=False)  # cloud URL
        latitude     = graphene.Float(required=True)
        longitude    = graphene.Float(required=True)
        accuracy     = graphene.Float(required=False)
        address      = graphene.String(required=False)
        captured_at  = graphene.String(required=True)   # ISO datetime string from device
        status       = graphene.String(required=False, default_value="Present")
        remarks      = graphene.String(required=False)

    @login_required
    def mutate(
        self, info, employee_id, latitude, longitude, captured_at,
        photo=None, photo_url=None, accuracy=None, address=None,
        status="Present", remarks=None
    ):
        try:
            emp = Employee.objects.get(id=employee_id, is_active=True)
        except Employee.DoesNotExist:
            return UploadAttendance(success=False, message="Employee not found")

        if not photo and not photo_url:
            return UploadAttendance(success=False, message="Either a photo file or photo_url is required")

        # Parse ISO datetime from mobile device
        try:
            captured_dt = datetime.fromisoformat(captured_at)
        except ValueError:
            return UploadAttendance(success=False, message="Invalid captured_at format. Use ISO 8601.")

        valid_statuses = ["Present", "Late", "Half Day", "Absent"]
        if status not in valid_statuses:
            return UploadAttendance(success=False, message=f"Invalid status. Choose: {valid_statuses}")

        # Prevent duplicate attendance for same employee same day
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
            captured_at=captured_dt,
            day=captured_dt.day,
            month=captured_dt.month,
            year=captured_dt.year,
            status=status,
            uploaded_by=info.context.user,
            remarks=remarks,
        )
        return UploadAttendance(success=True, message="Attendance uploaded successfully", attendance=att)


# ═════════════════════════════════════════════════════════════
#  M U T A T I O N   R O O T
# ═════════════════════════════════════════════════════════════

class Mutation(graphene.ObjectType):

    # Auth
    create_user     = CreateUser.Field()
    login_user      = LoginUser.Field()
    forgot_password = ForgotPassword.Field()
    reset_password  = ResetPassword.Field()

    # Standard JWT helpers
    token_auth    = graphql_jwt.ObtainJSONWebToken.Field()
    verify_token  = graphql_jwt.Verify.Field()
    refresh_token = graphql_jwt.Refresh.Field()

    # Employee
    create_employee = CreateEmployee.Field()
    update_employee = UpdateEmployee.Field()
    delete_employee = DeleteEmployee.Field()

    # Day-to-Day Monitoring screen
    add_day_to_day_entry = AddDayToDayEntry.Field()

    # Process screen
    add_process_entry = AddProcessEntry.Field()

    # Attendance screen
    upload_attendance = UploadAttendance.Field()


# ═════════════════════════════════════════════════════════════
#  S C H E M A
# ═════════════════════════════════════════════════════════════


schema = graphene.Schema(query=Query, mutation=Mutation)