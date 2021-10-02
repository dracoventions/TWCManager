$(document).ready(function() {
  $("#sendDebugCommand").click(function(e) {
    e.preventDefault();
    $.ajax({
      type: "POST",
      url: "/api/sendDebugCommand",
      data: JSON.stringify({
        commandName: $("#cmdDropdown").val(),
        customCommand: $("#cmdCustom").val()
      }),
    });
    setTimeout(function(){
      var lookup = $.ajax({
        type: "GET",
        url: "/api/getLastTWCResponse",
        data: {}
      })
      lookup.done(function(html) {
        $("#lastTWCResponse").val(html);
      });
    }, 3000);
  });

  $("#TeslaAPICommand").change(function () {

      if (this.value == "setChargeRate") {
        $("#TeslaAPIParams").val('{ "charge_rate": 5 }');
      }
      if (this.value == "wakeVehicle") {
        $("#TeslaAPIParams").val("{}");
      }
    });

  $("#sendTeslaAPICommand").click(function(e) {
    e.preventDefault();
    $.ajax({
      type: "POST",
      url: "/api/sendTeslaAPICommand",
      data: JSON.stringify({
        commandName: $("#TeslaAPICommand").val(),
        parameters: $("#TeslaAPIParams").val(),
        vehicleID: $("#TeslaAPIVehicle").val()
      }),
    });
  });
});

