// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Student", {
  setup: function (frm) {
    frm.add_fetch("guardian", "guardian_name", "guardian_name");
    frm.add_fetch("student", "title", "full_name");
    frm.add_fetch("student", "gender", "gender");
    frm.add_fetch("student", "date_of_birth", "date_of_birth");

    frm.set_query("student", "siblings", function (doc) {
      return {
        filters: {
          name: ["!=", doc.name],
        },
      };
    });
  },

  refresh: function (frm) {
    frm.set_query("user", function (doc) {
      return {
        filters: {
          ignore_user_type: 1,
        },
      };
    });

    if (!frm.is_new()) {
      // custom buttons
      frm.add_custom_button(__("Accounting Ledger"), function () {
        frappe.set_route("query-report", "General Ledger", {
          party_type: "Student",
          party: frm.doc.name,
        });
      });
    }

    frappe.db.get_value(
      "Education Settings",
      { name: "Education Settings" },
      "user_creation_skip",
      (r) => {
        if (cint(r.user_creation_skip) !== 1) {
          frm.set_df_property("student_email_id", "reqd", 1);
        }
      }
    );
  },

  select_all_months: function (frm) {
    frm.set_value("transportation_fee_structure_months", "");
    const monthNames = [
      "January",
      "February",
      "March",
      "April",
      "May",
      "June",
      "July",
      "August",
      "September",
      "October",
      "November",
      "December",
    ];

    // / Creating a date object
    for (let i = 0; i < 12; i++) {
      let num = i < 9 ? "0" + (i + 1) : i + 1;
      frm.add_child("transportation_fee_structure_months", {
        month_number: num,
        month_name: monthNames[parseInt(num - 1)],
      });
      refresh_field("transportation_fee_structure_months");
    }
  },
});

frappe.ui.form.on("Student Guardian", {
  guardians_add: function (frm) {
    frm.fields_dict["guardians"].grid.get_field("guardian").get_query =
      function (doc) {
        let guardian_list = [];
        if (!doc.__islocal) guardian_list.push(doc.guardian);
        $.each(doc.guardians, function (idx, val) {
          if (val.guardian) guardian_list.push(val.guardian);
        });
        return { filters: [["Guardian", "name", "not in", guardian_list]] };
      };
  },
});

frappe.ui.form.on("Student Sibling", {
  siblings_add: function (frm) {
    frm.fields_dict["siblings"].grid.get_field("student").get_query = function (
      doc
    ) {
      let sibling_list = [frm.doc.name];
      $.each(doc.siblings, function (idx, val) {
        if (val.student && val.studying_in_same_institute == "YES") {
          sibling_list.push(val.student);
        }
      });
      return { filters: [["Student", "name", "not in", sibling_list]] };
    };
  },
});

frappe.ui.form.on("Transportation Fee Structure Months", {
  month_number: function (frm, cdt, cdn) {
    // frm.set_value("transportation_fee_structure_months", "");
    const child = locals[cdt][cdn];
    const monthNames = [
      "January",
      "February",
      "March",
      "April",
      "May",
      "June",
      "July",
      "August",
      "September",
      "October",
      "November",
      "December",
    ];

    if (child.month_number) {
      child.month_name = monthNames[parseInt(child.month_number) - 1];
      frm.refresh_field("transportation_fee_structure_months"); // Refresh the child table field
    }
  },
});
