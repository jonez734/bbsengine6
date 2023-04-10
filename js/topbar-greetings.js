$(document).ready(function() {
  be.addinterval(5000, "update topbar.greetings", function() {
    be.updatetopbaritem("topbar.greetings", $("div#topbar .greetings"), "/get-topbar-greetings?callback=?");
  });
}); /* end document.ready() */
