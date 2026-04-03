/**
 * redirectpage.js - Redirect countdown timer
 * @description Displays countdown and redirects user after delay
 */
$(document).ready(function() {
  'use strict';

  const counterspan = $("div.redirectpage span.counter");
  const nounspan = $("div.redirectpage span.noun");

  if (counterspan.length === 0 || nounspan.length === 0) {
    return;
  }

  let counterval = parseInt(counterspan.html(), 10);
  if (isNaN(counterval)) {
    counterval = 0;
  }

  let redirectpagecountdownid = null;

  function updatecounter() {
    const noun = (counterval === 1) ? "second" : "seconds";
    counterspan.html(counterval);
    nounspan.html(noun);

    if (counterval === 0) {
      clearInterval(redirectpagecountdownid);
      redirectpagecountdownid = null;
      return;
    }
    counterval--;
  }

  redirectpagecountdownid = setInterval(updatecounter, 1000);
});