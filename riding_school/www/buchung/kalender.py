import frappe

no_cache = True

def get_context(context):
    # Nicht eingeloggt → zurück zum Login
    if frappe.session.user == "Guest":
        frappe.local.flags.redirect_location = "/buchung"
        raise frappe.Redirect

    # Rider-Daten laden
    rider = frappe.db.get_value(
        "RS Rider",
        {"user": frappe.session.user},
        ["name", "full_name", "skill_level", "weight_kg"],
        as_dict=True
    )

    context.no_header = True
    context.no_footer = True
    context.title = "Meine Buchungen"
    context.user_email = frappe.session.user
    context.rider = rider or {}

    # Zeitkarten laden
    if rider:
        time_cards = frappe.get_all(
            "RS Time Card",
            filters={"rider": rider.name, "status": "Active"},
            fields=["name", "total_lessons", "used_lessons", "remaining_lessons", "valid_until"]
        )
        context.time_cards = time_cards
    else:
        context.time_cards = []
