frappe.listview_settings["Fee Collections"] = {
  add_fields: ["docstatus", "is_return"],
  get_indicator: function (doc) {
    if (doc.is_return == 1) {
      return [__("Refund"), "gray", "is_return,=,1"];
    } else if (doc.docstatus == 1) {
      return [__("Paid"), "green", "docstatus,=,1"];
    }
  },
};
