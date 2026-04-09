app_name = "riding_school"
app_title = "Riding School"
app_publisher = "Svan GmbH"
app_description = "Riding school management for ERPNext"
app_email = "ronny.olm@svan.gmbh"
app_license = "mit"

add_to_apps_screen = [
    {
        "name": "riding_school",
        "logo": "/assets/riding_school/images/horse.svg",
        "title": "Riding School",
        "route": "/desk"
    }
]

fixtures = [
    {"dt": "DocType", "filters": [["module", "=", "Riding School"]]}
]

app_include_js = []
app_include_css = []

modules_to_load = ["Riding School"]
