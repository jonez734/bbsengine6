$(document).ready(function() {
  'use strict';
  const be = bbsengine();
  if (be !== null)
  {
    be.addinterval(5000, "update nav", function() {
      be.updatetopbaritem("nav", ".blurb .nav");
    });
  }
});
