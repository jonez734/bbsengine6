$(document).ready(function() {
  var redirectpagecountdownid = null;
  var counterspan = $("div.redirectpage span.counter");
  var nounspan = $("div.redirectpage span.noun");
  var counterval = counterspan.html();
  
  var be = getbbsengine();
  
  function updatecounter()
  {
//    be.logentry("updatecounter: "+counterval);
    if (counterval == 1)
    {
      noun = "second";
    }
    else
    {
      noun = "seconds";
    }
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
