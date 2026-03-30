$(document).ready(function() {
  'use strict';
  const be = bbsengine();
  if (be !== null)
  {
    be.addinterval(5000, "update topbar.loginlogout", function() {
      be.updatetopbaritem("topbar.loginlogout", ".loginlogout");
    });
  }
});
