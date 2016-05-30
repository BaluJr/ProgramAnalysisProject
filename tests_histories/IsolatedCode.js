a = new A();
switch (a) {
case a.cond1(): a.Test();
case a.cond2(): a.BLA();
}
b = new B()
b.test()



// Merging of objects on heap is working
/*a1 = new A();
b1 = new B();
c1 = new C();
a1.b = b1;
b1.c = c1;
a2 = new A();
b2 = new B();
b2.c = new C();

a1 = a2;
a2.b = b2

b2.c.TEST();*/


/*
// Array Access is NOT working
// We have to think about what to do with literals
var a = [];
a[0] = "a"; // new X();
a[1] = "a"; //new Y();
a[2] = "a"; //new Z()];
a[1].BAM(); */


/*// Conditionals are working
a = new A();
if (true) {
    a.optional1()
}

// Setting loop depth and special Tags is working
while (true) {
    a.Test1();
    while (a.Check()) {
        a.Test2()
    }
}

// Subfunctions are working with return types and inner scope
c = TestFunction(a)
function TestFunction (myParam) {
    a2 = new A();
    a2.doesNotBotherTheOtherA();
    myParam.InnerTest();
    return myParam;
}

// Anonymous objects that are used are kept in the history
anon = c.Test3()
anon.something()


// Aliasing works even over conditions (only merged when necessary)
if (True) {
    b = new B()
    b.optional2_1();
    a = b
    a.optional2_2()
}
a.Test4()






// The original Testcode
//(function()  {
//   var httpRequest;
//   document.getElementById("ajaxButton").onclick = (function()  {
//      makeRequest("test.html");
//   }
//);
//   function makeRequest(url)  {
//      httpRequest = new XMLHttpRequest();
//      if (! httpRequest)  {
//         alert("Giving up :( Cannot create an XMLHTTP instance");
//         return false;
//      }
//      httpRequest.onreadystatechange = alertContents;
//      httpRequest.open("GET", url);
//      httpRequest.send();
//   }
//;
//}
//)();*/
