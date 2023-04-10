$(document).ready(function() {
  var be = getbbsengine();

  be.addinterval(5000, "update join url", function () {
    be.updatetopbaritem("join", $("div#topbar .join"), "/get-topbar-join?callback=?");
  });
  return;
}); /* end document.ready() */
