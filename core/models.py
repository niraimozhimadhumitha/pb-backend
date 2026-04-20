from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin


# ─────────────────────────────────────────────────────────────
#  Custom User Manager
# ─────────────────────────────────────────────────────────────
class UserManager(BaseUserManager):
    def create_user(self, username, password=None, is_admin=False, is_active=True):
        if not username:
            raise ValueError("Users must have a username")
        user = self.model(username=username)
        user.set_password(password)
        user.admin = is_admin
        user.active = is_active
        user.save(using=self._db)
        return user

    def create_superuser(self, username, password=None):
        return self.create_user(username, password=password, is_admin=True)


# ─────────────────────────────────────────────────────────────
#  Custom User Model  (Login Screen)
# ─────────────────────────────────────────────────────────────
class User(AbstractBaseUser, PermissionsMixin):
    username   = models.CharField(max_length=150, unique=True)
    full_name  = models.CharField(max_length=255, blank=True, null=True)
    admin      = models.BooleanField(default=False)
    active     = models.BooleanField(default=True)

    # For "Forgot Password" flow
    reset_password_token   = models.CharField(max_length=255, blank=True, null=True)
    reset_password_expires = models.DateTimeField(blank=True, null=True)
    last_login_at          = models.DateTimeField(blank=True, null=True)

    USERNAME_FIELD  = "username"
    REQUIRED_FIELDS = []

    objects = UserManager()

    def __str__(self):
        return self.username

    @property
    def is_staff(self):
        return self.admin

    @property
    def is_superuser(self):
        return self.admin

    @property
    def is_active(self):
        return self.active


# ─────────────────────────────────────────────────────────────
#  Employee Model  (Process screen – Welder Name / ID dropdown)
# ─────────────────────────────────────────────────────────────
PROCESS_CHOICES = [
    ("Welding",  "Welding"),
    ("UT",       "UT"),
    ("Forming",  "Forming"),
    ("SR",       "SR"),
    ("Final UT", "Final UT"),
]

class Employee(models.Model):
    employee_id = models.CharField(max_length=50, unique=True)
    name        = models.CharField(max_length=255)
    process     = models.CharField(max_length=20, choices=PROCESS_CHOICES)
    designation = models.CharField(max_length=100, blank=True, null=True)
    department  = models.CharField(max_length=100, blank=True, null=True)
    phone       = models.CharField(max_length=10,  blank=True, null=True)
    is_active   = models.BooleanField(default=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} – {self.employee_id}"

    @property
    def dropdown_label(self):
        return f"{self.name} – {self.employee_id}"


# ─────────────────────────────────────────────────────────────
#  Day-to-Day Monitoring Model
# ─────────────────────────────────────────────────────────────
DAY_TO_DAY_PROCESS_CHOICES = [
    ("Welding", "Welding"),
    ("UT",      "UT"),
    ("Forming", "Forming"),
    ("SR",      "SR"),
]

class DayToDay(models.Model):
    process      = models.CharField(max_length=20, choices=DAY_TO_DAY_PROCESS_CHOICES)
    count        = models.PositiveIntegerField()          # 1–20 dropdown
    input_numbers = models.CharField(max_length=500, blank=True, null=True)  # free-text field
    submitted_by = models.ForeignKey(User, on_delete=models.CASCADE)
    date         = models.DateField(auto_now_add=True)
    day          = models.IntegerField()
    month        = models.IntegerField()
    year         = models.IntegerField()
    created_at   = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if self.date:
            self.day   = self.date.day
            self.month = self.date.month
            self.year  = self.date.year
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.process} – {self.count} on {self.date}"


# ─────────────────────────────────────────────────────────────
#  Process Entry Model  (worker-wise production)
# ─────────────────────────────────────────────────────────────
class ProcessEntry(models.Model):
    process       = models.CharField(max_length=20, choices=PROCESS_CHOICES)
    employee      = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="entries")
    employee_name = models.CharField(max_length=255)   # snapshot
    employee_id_snapshot   = models.CharField(max_length=50)    # snapshot
    
    count         = models.PositiveIntegerField()     # 1–20 dropdown
    pass_count = models.PositiveIntegerField(default=0)
    fail_count = models.PositiveIntegerField(default=0)
  
    submitted_by  = models.ForeignKey(User, on_delete=models.CASCADE)
    date          = models.DateField(auto_now_add=True)
    day           = models.IntegerField()
    month         = models.IntegerField()
    year          = models.IntegerField()
    created_at    = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        # Snapshot employee details at write time
        if self.employee_id:
            pass  # set externally via mutate
        if self.date:
            self.day   = self.date.day
            self.month = self.date.month
            self.year  = self.date.year
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.process} – {self.employee_name} – {self.count}"


# ─────────────────────────────────────────────────────────────
#  Attendance Model  (geo-tagged photo)
# ─────────────────────────────────────────────────────────────
ATTENDANCE_STATUS = [
    ("Present",  "Present"),
    ("Late",     "Late"),
    ("Half Day", "Half Day"),
    ("Absent",   "Absent"),
]

class Attendance(models.Model):
    employee      = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="attendance")
    employee_name = models.CharField(max_length=255)
    employee_id_snapshot = models.CharField(max_length=50)

    # Photo stored as a URL (uploaded to cloud/local storage)
    photo         = models.ImageField(upload_to="attendance_photos/", null=True, blank=True)
    photo_url     = models.URLField(max_length=1000, blank=True, null=True)

    # Geo-tag
    latitude      = models.DecimalField(max_digits=9, decimal_places=6)
    longitude     = models.DecimalField(max_digits=9, decimal_places=6)
    accuracy      = models.FloatField(null=True, blank=True)
    address       = models.CharField(max_length=500, blank=True, null=True)

    # Timestamp from device at moment of capture
    captured_at   = models.DateTimeField()
    day           = models.IntegerField()
    month         = models.IntegerField()
    year          = models.IntegerField()

    status        = models.CharField(max_length=10, choices=ATTENDANCE_STATUS, default="Present")
    uploaded_by   = models.ForeignKey(User, on_delete=models.CASCADE)
    remarks       = models.TextField(blank=True, null=True)
    created_at    = models.DateTimeField(auto_now_add=True)

    class Meta:
        # One attendance record per employee per day
        unique_together = ("employee", "day", "month", "year")

    def save(self, *args, **kwargs):
        if self.captured_at:
            self.day   = self.captured_at.day
            self.month = self.captured_at.month
            self.year  = self.captured_at.year
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.employee_name} – {self.captured_at.date()}"


# ─────────────────────────────────────────────────────────────
#  Dashboard – Cumulative Total  (single-row table)
# ─────────────────────────────────────────────────────────────
class DashboardTotal(models.Model):
    key           = models.CharField(max_length=20, default="GLOBAL", unique=True)
    total_welding = models.PositiveBigIntegerField(default=0)
    total_ut      = models.PositiveBigIntegerField(default=0)
    total_forming = models.PositiveBigIntegerField(default=0)
    total_sr      = models.PositiveBigIntegerField(default=0)
    total_final_ut = models.PositiveBigIntegerField(default=0)
    last_updated  = models.DateTimeField(auto_now=True)

    def __str__(self):
        return "Global Dashboard Totals"


# ─────────────────────────────────────────────────────────────
#  Dashboard – Daily Production Snapshot
# ─────────────────────────────────────────────────────────────
class DailyProduction(models.Model):
    day      = models.IntegerField()
    month    = models.IntegerField()
    year     = models.IntegerField()
    welding  = models.PositiveBigIntegerField(default=0)
    ut       = models.PositiveBigIntegerField(default=0)
    forming  = models.PositiveBigIntegerField(default=0)
    sr       = models.PositiveBigIntegerField(default=0)
    final_ut = models.PositiveBigIntegerField(default=0)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("day", "month", "year")

    def __str__(self):
        return f"Daily – {self.day}/{self.month}/{self.year}"


# ─────────────────────────────────────────────────────────────
#  Dashboard – Monthly Production Snapshot
# ─────────────────────────────────────────────────────────────
class MonthlyProduction(models.Model):
    month    = models.IntegerField()
    year     = models.IntegerField()
    welding  = models.PositiveBigIntegerField(default=0)
    ut       = models.PositiveBigIntegerField(default=0)
    forming  = models.PositiveBigIntegerField(default=0)
    sr       = models.PositiveBigIntegerField(default=0)
    final_ut = models.PositiveBigIntegerField(default=0)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("month", "year")

    def __str__(self):
        return f"Monthly – {self.month}/{self.year}"


# ─────────────────────────────────────────────────────────────
#  Dashboard – Yearly Production Snapshot
# ─────────────────────────────────────────────────────────────
class YearlyProduction(models.Model):
    year     = models.IntegerField(unique=True)
    welding  = models.PositiveBigIntegerField(default=0)
    ut       = models.PositiveBigIntegerField(default=0)
    forming  = models.PositiveBigIntegerField(default=0)
    sr       = models.PositiveBigIntegerField(default=0)
    final_ut = models.PositiveBigIntegerField(default=0)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Yearly – {self.year}"
