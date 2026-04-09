from frappe import _

def get_data():
    return [
        {
            "label": _("Planung"),
            "icon": "fa fa-calendar",
            "items": [
                {
                    "type": "doctype",
                    "name": "RS Lesson Slot",
                    "label": _("Zeitslots"),
                    "description": _("Reitstunden planen")
                },
                {
                    "type": "doctype",
                    "name": "RS Booking",
                    "label": _("Buchungen"),
                    "description": _("Buchungen verwalten")
                }
            ]
        },
        {
            "label": _("Stammdaten"),
            "icon": "fa fa-database",
            "items": [
                {
                    "type": "doctype",
                    "name": "RS Horse",
                    "label": _("Pferde"),
                    "description": _("Pferde verwalten")
                },
                {
                    "type": "doctype",
                    "name": "RS Instructor",
                    "label": _("Reitlehrer"),
                    "description": _("Reitlehrer verwalten")
                },
                {
                    "type": "doctype",
                    "name": "RS Rider",
                    "label": _("Reitschüler"),
                    "description": _("Reitschüler verwalten")
                },
                {
                    "type": "doctype",
                    "name": "RS Facility",
                    "label": _("Reitplätze"),
                    "description": _("Reitplätze verwalten")
                }
            ]
        },
        {
            "label": _("Abrechnung"),
            "icon": "fa fa-money",
            "items": [
                {
                    "type": "doctype",
                    "name": "RS Time Card",
                    "label": _("Zeitkarten"),
                    "description": _("10er Karten verwalten")
                }
            ]
        }
    ]
