$(document).ready(function() {
  'use strict';
  let redirectpagecountdownid = null;
  const counterspan = $("div.redirectpage span.counter");
  const nounspan = $("div.redirectpage span.noun");
  let counterval = counterspan.html();
  
  function updatecounter()
  {
    const noun = (counterval == 1) ? "second" : "seconds";
    counterspan.html(counterval);
    nounspan.html(noun);
    if (counterval == 0)
    {
      clearInterval(redirectpagecountdownid);
      redirectpagecountdownid = null;
      return;
    }
    counterval--;
  }
  
  redirectpagecountdownid = setInterval(updatecounter, 1000);
});
