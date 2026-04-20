from .models import DashboardTotal, DailyProduction, MonthlyProduction, YearlyProduction

def update_dashboard_counters(process, count, today):

    # GLOBAL
    dashboard, _ = DashboardTotal.objects.get_or_create(key="GLOBAL")

    if process == "Welding":
        dashboard.total_welding += count
    elif process == "UT":
        dashboard.total_ut += count
    elif process == "Forming":
        dashboard.total_forming += count
    elif process == "SR":
        dashboard.total_sr += count
    elif process == "Final UT":
        dashboard.total_final_ut += count

    dashboard.save()

    # DAILY
    daily, _ = DailyProduction.objects.get_or_create(
        day=today.day, month=today.month, year=today.year
    )

    if process == "Welding":
        daily.welding += count
    elif process == "UT":
        daily.ut += count
    elif process == "Forming":
        daily.forming += count
    elif process == "SR":
        daily.sr += count
    elif process == "Final UT":
        daily.final_ut += count

    daily.save()

    # MONTHLY
    monthly, _ = MonthlyProduction.objects.get_or_create(
        month=today.month, year=today.year
    )

    if process == "Welding":
        monthly.welding += count
    elif process == "UT":
        monthly.ut += count
    elif process == "Forming":
        monthly.forming += count
    elif process == "SR":
        monthly.sr += count
    elif process == "Final UT":
        monthly.final_ut += count

    monthly.save()

    # YEARLY
    yearly, _ = YearlyProduction.objects.get_or_create(
        year=today.year
    )

    if process == "Welding":
        yearly.welding += count
    elif process == "UT":
        yearly.ut += count
    elif process == "Forming":
        yearly.forming += count
    elif process == "SR":
        yearly.sr += count
    elif process == "Final UT":
        yearly.final_ut += count

    yearly.save()