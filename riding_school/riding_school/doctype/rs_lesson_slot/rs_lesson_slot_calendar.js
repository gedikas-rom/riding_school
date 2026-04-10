frappe.views.calendar["RS Lesson Slot"] = {
    field_map: {
        start: "start",
        end: "end",
        id: "name",
        title: "title",
        allDay: "allDay",
        color: "color"
    },
    gantt: false,
    get_events_method: "riding_school.riding_school.api.slot_generator.get_calendar_events",
    firstDay: 1
};
