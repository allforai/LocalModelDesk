ObjC.import('CoreGraphics'); ObjC.import('Foundation');
var l=ObjC.deepUnwrap(ObjC.castRefToObject($.CGWindowListCopyWindowInfo(0,0)));
var o=l.filter(w=>/LocalModelDesk/.test(w.kCGWindowOwnerName||'')).map(w=>({owner:w.kCGWindowOwnerName,pid:w.kCGWindowOwnerPID,name:w.kCGWindowName,onscreen:w.kCGWindowIsOnscreen,layer:w.kCGWindowLayer,b:w.kCGWindowBounds}));
JSON.stringify({n:o.length,windows:o});
