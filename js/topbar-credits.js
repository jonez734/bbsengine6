$(document).ready(function() {
  var be = getbbsengine();

  be.addinterval(5000, "update credit count", function () {
    be.updatetopbaritem("credits", $("div#topbar .credits"), "/get-credit-count?callback=?");
  });
  return;
}); /* end document.ready() */
