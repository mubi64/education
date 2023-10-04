// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Transportation Fee Schedule", {
  refresh: async function (frm) {
	// if (
	// 	!frm.doc.__islocal &&
	// 	frm.doc.__onload &&
	// 	frm.doc.__onload.dashboard_info &&
	// 	frm.doc.fee_creation_status === "Successful"
	//   ) {
	// 	var info = frm.doc.__onload.dashboard_info;
	// 	frm.dashboard.add_indicator(
	// 	  __("Total Collected: {0}", [
	// 		format_currency(info.total_paid, info.currency),
	// 	  ]),
	// 	  "blue"
	// 	);
	// 	frm.dashboard.add_indicator(
	// 	  __("Total Outstanding: {0}", [
	// 		format_currency(info.total_unpaid, info.currency),
	// 	  ]),
	// 	  info.total_unpaid ? "orange" : "green"
	// 	);
	// }
	if (frm.doc.fee_creation_status === "In Process") {
		frm.dashboard.add_progress("Fee Creation Status", "0");
	}

    if (frm.doc.docstatus == 0) {
      frm.add_custom_button(__("Get Transportation Student"), function () {
        frappe.call({
          method: "get_transportation_student_count",
          doc: frm.doc,
          callback: function (r) {
            frm.set_value("total_student", r.message);
          },
        });
      });
    }

    if (frm.doc.docstatus == 1) {
      frm
        .add_custom_button(__("Create Fee"), function () {
          frappe.call({
            method: "create_fees",
            doc: frm.doc,
            callback: function (r) {
              frm.refresh();
            },
          });
        })
        .addClass("btn-primary");
    }
  },

  taxes_and_charges: function (frm) {
    frm.set_value("taxes", "");
    if (frm.doc.taxes_and_charges) {
      frappe.call({
        method: "education.education.api.get_fee_sales_charges",
        args: {
          taxes_and_charges: frm.doc.taxes_and_charges,
        },
        callback: function (r) {
          if (r.message) {
            $.each(r.message, function (i, d) {
              var row = frappe.model.add_child(
                frm.doc,
                "Sales Taxes and Charges",
                "taxes"
              );
              row.charge_type = d.charge_type;
              row.account_head = d.account_head;
              row.rate = d.rate;
              row.cost_center = d.cost_center;
              row.description = d.description;
            });
          }
          refresh_field("taxes");
        },
      });
    }
  },
});
