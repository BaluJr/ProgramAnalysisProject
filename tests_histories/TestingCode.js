// Handling anonymous functions including possibly anonymous local vars
/*function A (tstObj) {
    tstObj.X();
    tstObj.Y();
    tstFn(tstObj);
}*/


// Recursion safety
/*obj = new Obj();
function A (tstObj) {
    tstObj.inner();
    A(tstObj);
}
A(obj);*/

// Merging of objects on heap is working
/*function A() {
a1 = new A();
b1 = new B();
c1 = new C();
c1.operationForOnlyC1();
a1.b = b1;
b1.c = c1;
a2 = new A();
b2 = new B();
b2.c = new C();
b2.c.operationForOnlyC2();
a1 = a2;
// With steensgaard, at this position not only b and b2, but also c and c2 have to be merged
a2.b = b2;
// So this operation belongs to both C objects
b2.c.TEST();
};*/


/* Complicated encapsulations are working
function tstFn (para) {
    para.blub();
    innerFn(para);
}
for (var i = 1; i < 4; i++) {
    a = new A();
    c = (function (tst) {
        tst.Bam();
        for (cur in {"a":1, "b" : 2, "c" : 3}) {
            f.Bam(null, tst);
        };
        var b = tst;
        tstFn(b);
        return b;
    })(a)

    if (true) {
    c.GrandeFinale();
    }
}

function innerFn(innerPara) {
    if (i == 5) {
    innerInnerFunction(null, innerPara);
    }
    else
    {
     innerInnerFunctionAlternative(innerPara);
    }
}*/



//a = new x.google.y.Camera()
//a.Open()
//a.Close()


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
//)();

//a = new T() || new Z();
//a.test();


//// Switch Case working
//a = new A();
//switch (a) {
//case a.cond1(): a.Test();
//case a.cond2(): a.BLA();
//}
//b = new B()
//b.test()





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
a.Test4()*/