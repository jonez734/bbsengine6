$(document).ready(function() {
  if (be !== null)
  {
    be.addinterval(5000, "update nav", function() {
      be.updatetopbaritem("nav", $(".blurb .nav"), "/get-nav?callback=?");
    });
  }
  return;
}); /* end document.ready() */
