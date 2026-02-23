$(document).ready(function () {

    async function checkcurrentmemberid()
    {
        currentmoniker = await bbsengine().getcurrentmoniker();
        bbsengine().logentry("currentmoniker="+JSON.stringify(currentmoniker));
        return;
    }
});

// console.log("checkcurrentmemberid.100: be="+JSON.stringify(be));
//inerval = be.gettopbarupdateinterval();
/*
be.gettopbarupdateinterval().then(interval => { 
    be.addinterval(interval, "checkcurrentmemberid", checkcurrentmemberid);
    be.logentry("checkcurrentmemberid.110: updateinterval="+interval); 
})
.catch(error => {
    be.logentry(error);
});
*/
