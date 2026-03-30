$(document).ready(function() {
  'use strict';
  const be = bbsengine();

  if (be !== undefined)
  {
    be.addinterval(5000, "update credit count", function () {
      be.updatetopbaritem("topbar.credits", ".credits");
    });
  }
});
