$(document).ready(function() {
  be.addinterval(5000, "update nav", function() {
//    be.logentry("topbar-nav: called");
    be.updatetopbaritem("nav", $(".blurb .nav"), "/get-nav?callback=?");
  });
}); /* end document.ready() */
