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
    list_display = ('username', 'full_name', 'admin', 'active', 'access_level')
    list_filter = ('admin', 'active')

    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal Info', {'fields': ('full_name',)}),
        ('Permissions', {
            'fields': ('admin', 'active', 'groups', 'user_permissions'),
            'description': (
                '⚠️ Access Rules:\n'
                '• active=ON  + admin=OFF → Attendance screen only.\n'
                '• active=ON  + admin=ON  → All screens (Attendance + Process + Day Monitoring).\n'
                '• active=OFF             → No access (login blocked).'
            ),
        }),
        ('Reset Info', {'fields': ('reset_password_token', 'reset_password_expires')}),
        ('Dates', {'fields': ('last_login_at',)}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'password1', 'password2', 'full_name', 'admin', 'active'),
        }),
    )

    search_fields = ('username', 'full_name')
    ordering = ('username',)
    filter_horizontal = ('groups', 'user_permissions')

    # ── Computed column: shows access level in the user list ──
    @admin.display(description='Access Level')
    def access_level(self, obj):
        if not obj.active:
            return '🔴 No Access'
        if obj.active and not obj.admin:
            return '🟡 Attendance Only'
        if obj.active and obj.admin:
            return '🟢 Full Access'
        return '—'


# ─────────────────────────────
# EMPLOYEE ADMIN
# ─────────────────────────────
@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ('employee_id', 'name', 'process', 'is_active')
    list_filter = ('process', 'is_active')
    search_fields = ('name', 'employee_id')


# ─────────────────────────────
# ATTENDANCE ADMIN
# ─────────────────────────────
@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = (
        'employee_name',
        'employee_id_snapshot',
        'status',
        'in_time',
        'out_time',
        'captured_at',
        'latitude',
        'longitude',
    )
    list_filter = ('status', 'day', 'month', 'year')
    search_fields = ('employee_name', 'employee_id_snapshot')
    readonly_fields = ('created_at', 'in_time', 'out_time', 'captured_at')


# ─────────────────────────────
# PROCESS ENTRY ADMIN
# ─────────────────────────────
@admin.register(ProcessEntry)
class ProcessEntryAdmin(admin.ModelAdmin):
    list_display = ('process', 'employee_name', 'count', 'pass_count', 'fail_count', 'date')
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