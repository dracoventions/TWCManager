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
});

