
$(document).ready(function() {
  $("#cancel_chargenow").click(function(e) {
    e.preventDefault();
    $.ajax({
      type: "POST",
      url: "/api/cancelChargeNow",
      data: {}
    });
  });
});

$(document).ready(function() {
  $("#send_start_command").click(function(e) {
    e.preventDefault();
    $.ajax({
      type: "POST",
      url: "/api/sendStartCommand",
      data: {}
    });
  });
});

$(document).ready(function() {
  $("#send_stop_command").click(function(e) {
    e.preventDefault();
    $.ajax({
      type: "POST",
      url: "/api/sendStopCommand",
      data: {}
    });
  });
});

function loadVIN(twc, vin) {
  window.open("/vehicleDetails/" + document.getElementById(twc+"_"+vin+"VIN").innerHTML, '_blank');
}
