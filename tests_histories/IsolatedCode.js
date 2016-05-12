(
function TEST ()  {
   var httpRequest;
   document.getElementById("ajaxButton").onclick = function()  {
      makeRequest("test.html");
   }
;

   function open(req, url) {

};


   function makeRequest(url)  {
      httpRequest = new XMLHttpRequest();
      if (! httpRequest)  {
         alert("Giving up :( Cannot create an XMLHTTP instance");
         return false;
      }
      httpRequest.onreadystatechange = alertContents;	
      open(a,n) ;
      Test1.doSomething();
      httpRequest.open("GET", url);
      httpRequest.send();
   }
;
}
)();

