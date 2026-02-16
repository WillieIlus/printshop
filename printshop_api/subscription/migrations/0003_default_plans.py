# Generated migration - ensure default plans exist

from django.db import migrations


def create_default_plans(apps, schema_editor):
    SubscriptionPlan = apps.get_model("subscription", "SubscriptionPlan")
    if SubscriptionPlan.objects.exists():
        return
    SubscriptionPlan.objects.create(
        name="Starter",
        plan_type="STARTER",
        billing_period="MONTHLY",
        price=0,
        max_printing_machines=1,
        max_finishing_machines=0,
        max_users=1,
        max_quotes_per_month=100,
        max_products=50,
        is_active=True,
    )
    SubscriptionPlan.objects.create(
        name="Professional",
        plan_type="PROFESSIONAL",
        billing_period="MONTHLY",
        price=2999,
        max_printing_machines=3,
        max_finishing_machines=2,
        max_users=5,
        max_quotes_per_month=500,
        max_products=200,
        is_active=True,
    )
    SubscriptionPlan.objects.create(
        name="Enterprise",
        plan_type="ENTERPRISE",
        billing_period="MONTHLY",
        price=9999,
        max_printing_machines=0,  # unlimited
        max_finishing_machines=0,  # unlimited
        max_users=20,
        max_quotes_per_month=0,  # unlimited
        max_products=0,  # unlimited
        is_active=True,
    )


def reverse_create_default_plans(apps, schema_editor):
    SubscriptionPlan = apps.get_model("subscription", "SubscriptionPlan")
    SubscriptionPlan.objects.filter(
        plan_type__in=["STARTER", "PROFESSIONAL", "ENTERPRISE"]
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("subscription", "0002_add_plan_limits_and_mpesa_stk"),
    ]

    operations = [
        migrations.RunPython(create_default_plans, reverse_create_default_plans),
    ]
