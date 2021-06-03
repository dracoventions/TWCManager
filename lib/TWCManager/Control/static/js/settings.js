$(document).ready(function() {
  $("#addOffset").click(function(e) {
    e.preventDefault();
    $.ajax({
      type: "POST",
      url: "/api/addConsumptionOffset",
      data: JSON.stringify({
        offsetName: $("#offsetName").val(),
        offsetValue: $("#offsetValue").val(),
        offsetUnit: $("#offsetUnit").val()
      }),
      dataType: "json"
    });
  });
});

// Draw the buttons which appear in the Action column next to each entry in the Consumption Offset
// table
function offsetActionButtons(key, value, unit) {
  var actionButtons = "<td colspan = 2>";
  actionButtons += "<button type='button' class='btn btn-danger btn-sm' onClick='deleteOffset(\"" + key + "\")'>Delete</button>";
  actionButtons += " &nbsp; ";
  actionButtons += "<button type='button' class='btn btn-success btn-sm' onClick='editOffset(\"" + key + "\",\"" + value +"\",\"" + unit + "\")'>Edit</button>";
  actionButtons += "</td>";
  return actionButtons;
}

function deleteOffset(key) {
  $.ajax({
    type: "POST",
    url: "/api/deleteConsumptionOffset",
    data: JSON.stringify({
      offsetName: key
    }),
    dataType: "json"
  });
}

function editOffset(key, value, unit) {
  $("#offsetName").val(key)
  $("#offsetValue").val(value)
  $("#offsetUnit").val(unit)
}

// AJAJ refresh for getConsumptionOffset call
$(document).ready(function() {
    function getConsumptionOffset() {
        $.ajax({
            url: "/api/getConsumptionOffsets",
            dataType: "text",
            cache: false,
            success: function(data) {
                var json = $.parseJSON(data);
                $("#consumptionOffsets tbody").empty();
                Object.keys(json).sort().forEach(function(key) {
                  $('#consumptionOffsets tbody').append("<tr><td>"+key+"</td><td>"+json[key]['value']+ " " + json[key]["unit"] + "</td>" + offsetActionButtons(key, json[key]['value'], json[key]["unit"]) + "</tr>");
                });
            }
        });
        setTimeout(getConsumptionOffset, 2000);
    }

    getConsumptionOffset();
});

