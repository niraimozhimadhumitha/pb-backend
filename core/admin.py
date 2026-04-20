from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import (
    User,
    Employee,
    Attendance,
    DayToDay,
    ProcessEntry,
    DashboardTotal,
    DailyProduction,
    MonthlyProduction,
    YearlyProduction
)

# ─────────────────────────────
# USER ADMIN (LOGIN SYSTEM)
# ─────────────────────────────
@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'admin', 'active')
    list_filter = ('admin', 'active')

    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal Info', {'fields': ('full_name',)}),
        ('Permissions', {'fields': ('admin', 'active', 'groups', 'user_permissions')}),
        ('Reset Info', {'fields': ('reset_password_token', 'reset_password_expires')}),
        ('Dates', {'fields': ('last_login_at',)}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'password1', 'password2', 'admin', 'active'),
        }),
    )

    search_fields = ('username',)
    ordering = ('username',)
    filter_horizontal = ('groups', 'user_permissions')


# ─────────────────────────────
# EMPLOYEE ADMIN
# ─────────────────────────────
@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ('employee_id', 'name', 'process', 'is_active')
    list_filter = ('process', 'is_active')
    search_fields = ('name', 'employee_id')


# ─────────────────────────────
# ATTENDANCE ADMIN (IMPORTANT)
# ─────────────────────────────
@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = (
        'employee_name',
        'employee_id_snapshot',
        'status',
        'captured_at',
        'latitude',
        'longitude'
    )
    list_filter = ('status', 'day', 'month', 'year')
    search_fields = ('employee_name', 'employee_id_snapshot')
    readonly_fields = ('created_at',)


# ─────────────────────────────
# PROCESS ENTRY ADMIN
# ─────────────────────────────
@admin.register(ProcessEntry)
class ProcessEntryAdmin(admin.ModelAdmin):
    list_display = ('process', 'employee_name', 'count', 'date')
    list_filter = ('process', 'day', 'month', 'year')


# ─────────────────────────────
# DAY TO DAY ADMIN
# ─────────────────────────────
@admin.register(DayToDay)
class DayToDayAdmin(admin.ModelAdmin):
    list_display = ('process', 'count', 'date', 'submitted_by')
    list_filter = ('process', 'day', 'month', 'year')


# ─────────────────────────────
# DASHBOARD ADMIN (read-only style)
# ─────────────────────────────
admin.site.register(DashboardTotal)
admin.site.register(DailyProduction)
admin.site.register(MonthlyProduction)
admin.site.register(YearlyProduction)