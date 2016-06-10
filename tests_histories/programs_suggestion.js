var xmlhttp = new XMLHttpRequest();
var url = "myTutorials.txt";
xmlhttp.onreadystatechange = (function()  {
   if (xmlhttp.readyState == 4 && xmlhttp.status == 200)  {
      var myArr = JSON.parse(xmlhttp.responseText);
      myFunction(myArr);
   }
}
);
xmlhttp._questionmark_();



var xmlhttp = new XMLHttpRequest();
var url = "myTutorials.txt";
xmlhttp.onreadystatechange = (function()  {
   if (xmlhttp.readyState == 4 && xmlhttp.status == 200)  {
      var myArr = JSON.parse(xmlhttp.responseText);
      myFunction(myArr);
   }
}
);
xmlhttp.open("GET", url, true);
xmlhttp._questionmark_();



(function()  {
   var httpRequest;
   document.getElementById("ajaxButton").onclick = (function()  {
      makeRequest("test.html");
   }
);
   function makeRequest(url)  {
      httpRequest = new XMLHttpRequest();
      if (! httpRequest)  {
         alert("Giving up :( Cannot create an XMLHTTP instance");
         return false;
      }
      httpRequest.onreadystatechange = alertContents;
      httpRequest._questionmark_();
   }
;
}
)();



(function()  {
   var httpRequest;
   document.getElementById("ajaxButton").onclick = (function()  {
      makeRequest("test.html");
   }
);
   function makeRequest(url)  {
      httpRequest = new XMLHttpRequest();
      if (! httpRequest)  {
         alert("Giving up :( Cannot create an XMLHTTP instance");
         return false;
      }
      httpRequest.onreadystatechange = alertContents;
      httpRequest.open("GET", url);
      httpRequest._questionmark_();
   }
;
}
)();




