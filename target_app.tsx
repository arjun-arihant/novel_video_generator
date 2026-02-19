import { createHotContext as __vite__createHotContext } from "/@vite/client";import.meta.hot = __vite__createHotContext("/src/App.tsx");import __vite__cjsImport0_react_jsxDevRuntime from "/node_modules/.vite/deps/react_jsx-dev-runtime.js?v=9200eed5"; const jsxDEV = __vite__cjsImport0_react_jsxDevRuntime["jsxDEV"];
import * as RefreshRuntime from "/@react-refresh";
const inWebWorker = typeof WorkerGlobalScope !== "undefined" && self instanceof WorkerGlobalScope;
let prevRefreshReg;
let prevRefreshSig;
if (import.meta.hot && !inWebWorker) {
  if (!window.$RefreshReg$) {
    throw new Error(
      "@vitejs/plugin-react can't detect preamble. Something is wrong."
    );
  }
  prevRefreshReg = window.$RefreshReg$;
  prevRefreshSig = window.$RefreshSig$;
  window.$RefreshReg$ = RefreshRuntime.getRefreshReg("D:/repos/buildbrief/client/src/App.tsx");
  window.$RefreshSig$ = RefreshRuntime.createSignatureFunctionForTransform;
}
import { BrowserRouter, Routes, Route } from "/node_modules/.vite/deps/react-router-dom.js?v=9200eed5";
import { HelmetProvider } from "/node_modules/.vite/deps/react-helmet-async.js?v=9200eed5";
import { ThemeProvider } from "/src/context/ThemeContext.tsx";
import { Layout } from "/src/components/layout/Layout.tsx";
import {
  LandingPage,
  FeaturesPage,
  PricingPage,
  AboutPage,
  BlogPage,
  ContactPage,
  AppPage
} from "/src/pages/index.ts?t=1771497884488";
function App() {
  return /* @__PURE__ */ jsxDEV(HelmetProvider, { children: /* @__PURE__ */ jsxDEV(ThemeProvider, { children: /* @__PURE__ */ jsxDEV(BrowserRouter, { children: /* @__PURE__ */ jsxDEV(Routes, { children: [
    /* @__PURE__ */ jsxDEV(Route, { path: "/", element: /* @__PURE__ */ jsxDEV(Layout, { children: /* @__PURE__ */ jsxDEV(LandingPage, {}, void 0, false, {
      fileName: "D:/repos/buildbrief/client/src/App.tsx",
      lineNumber: 41,
      columnNumber: 46
    }, this) }, void 0, false, {
      fileName: "D:/repos/buildbrief/client/src/App.tsx",
      lineNumber: 41,
      columnNumber: 38
    }, this) }, void 0, false, {
      fileName: "D:/repos/buildbrief/client/src/App.tsx",
      lineNumber: 41,
      columnNumber: 13
    }, this),
    /* @__PURE__ */ jsxDEV(Route, { path: "/features", element: /* @__PURE__ */ jsxDEV(Layout, { children: /* @__PURE__ */ jsxDEV(FeaturesPage, {}, void 0, false, {
      fileName: "D:/repos/buildbrief/client/src/App.tsx",
      lineNumber: 42,
      columnNumber: 54
    }, this) }, void 0, false, {
      fileName: "D:/repos/buildbrief/client/src/App.tsx",
      lineNumber: 42,
      columnNumber: 46
    }, this) }, void 0, false, {
      fileName: "D:/repos/buildbrief/client/src/App.tsx",
      lineNumber: 42,
      columnNumber: 13
    }, this),
    /* @__PURE__ */ jsxDEV(Route, { path: "/pricing", element: /* @__PURE__ */ jsxDEV(Layout, { children: /* @__PURE__ */ jsxDEV(PricingPage, {}, void 0, false, {
      fileName: "D:/repos/buildbrief/client/src/App.tsx",
      lineNumber: 43,
      columnNumber: 53
    }, this) }, void 0, false, {
      fileName: "D:/repos/buildbrief/client/src/App.tsx",
      lineNumber: 43,
      columnNumber: 45
    }, this) }, void 0, false, {
      fileName: "D:/repos/buildbrief/client/src/App.tsx",
      lineNumber: 43,
      columnNumber: 13
    }, this),
    /* @__PURE__ */ jsxDEV(Route, { path: "/about", element: /* @__PURE__ */ jsxDEV(Layout, { children: /* @__PURE__ */ jsxDEV(AboutPage, {}, void 0, false, {
      fileName: "D:/repos/buildbrief/client/src/App.tsx",
      lineNumber: 44,
      columnNumber: 51
    }, this) }, void 0, false, {
      fileName: "D:/repos/buildbrief/client/src/App.tsx",
      lineNumber: 44,
      columnNumber: 43
    }, this) }, void 0, false, {
      fileName: "D:/repos/buildbrief/client/src/App.tsx",
      lineNumber: 44,
      columnNumber: 13
    }, this),
    /* @__PURE__ */ jsxDEV(Route, { path: "/blog", element: /* @__PURE__ */ jsxDEV(Layout, { children: /* @__PURE__ */ jsxDEV(BlogPage, {}, void 0, false, {
      fileName: "D:/repos/buildbrief/client/src/App.tsx",
      lineNumber: 45,
      columnNumber: 50
    }, this) }, void 0, false, {
      fileName: "D:/repos/buildbrief/client/src/App.tsx",
      lineNumber: 45,
      columnNumber: 42
    }, this) }, void 0, false, {
      fileName: "D:/repos/buildbrief/client/src/App.tsx",
      lineNumber: 45,
      columnNumber: 13
    }, this),
    /* @__PURE__ */ jsxDEV(Route, { path: "/blog/:id", element: /* @__PURE__ */ jsxDEV(Layout, { children: /* @__PURE__ */ jsxDEV(BlogPage, {}, void 0, false, {
      fileName: "D:/repos/buildbrief/client/src/App.tsx",
      lineNumber: 46,
      columnNumber: 54
    }, this) }, void 0, false, {
      fileName: "D:/repos/buildbrief/client/src/App.tsx",
      lineNumber: 46,
      columnNumber: 46
    }, this) }, void 0, false, {
      fileName: "D:/repos/buildbrief/client/src/App.tsx",
      lineNumber: 46,
      columnNumber: 13
    }, this),
    /* @__PURE__ */ jsxDEV(Route, { path: "/contact", element: /* @__PURE__ */ jsxDEV(Layout, { children: /* @__PURE__ */ jsxDEV(ContactPage, {}, void 0, false, {
      fileName: "D:/repos/buildbrief/client/src/App.tsx",
      lineNumber: 47,
      columnNumber: 53
    }, this) }, void 0, false, {
      fileName: "D:/repos/buildbrief/client/src/App.tsx",
      lineNumber: 47,
      columnNumber: 45
    }, this) }, void 0, false, {
      fileName: "D:/repos/buildbrief/client/src/App.tsx",
      lineNumber: 47,
      columnNumber: 13
    }, this),
    /* @__PURE__ */ jsxDEV(Route, { path: "/app", element: /* @__PURE__ */ jsxDEV(AppPage, {}, void 0, false, {
      fileName: "D:/repos/buildbrief/client/src/App.tsx",
      lineNumber: 50,
      columnNumber: 41
    }, this) }, void 0, false, {
      fileName: "D:/repos/buildbrief/client/src/App.tsx",
      lineNumber: 50,
      columnNumber: 13
    }, this)
  ] }, void 0, true, {
    fileName: "D:/repos/buildbrief/client/src/App.tsx",
    lineNumber: 39,
    columnNumber: 11
  }, this) }, void 0, false, {
    fileName: "D:/repos/buildbrief/client/src/App.tsx",
    lineNumber: 38,
    columnNumber: 9
  }, this) }, void 0, false, {
    fileName: "D:/repos/buildbrief/client/src/App.tsx",
    lineNumber: 37,
    columnNumber: 7
  }, this) }, void 0, false, {
    fileName: "D:/repos/buildbrief/client/src/App.tsx",
    lineNumber: 36,
    columnNumber: 5
  }, this);
}
_c = App;
export default App;
var _c;
$RefreshReg$(_c, "App");
if (import.meta.hot && !inWebWorker) {
  window.$RefreshReg$ = prevRefreshReg;
  window.$RefreshSig$ = prevRefreshSig;
}
if (import.meta.hot && !inWebWorker) {
  RefreshRuntime.__hmr_import(import.meta.url).then((currentExports) => {
    RefreshRuntime.registerExportsForReactRefresh("D:/repos/buildbrief/client/src/App.tsx", currentExports);
    import.meta.hot.accept((nextExports) => {
      if (!nextExports) return;
      const invalidateMessage = RefreshRuntime.validateRefreshBoundaryAndEnqueueUpdate("D:/repos/buildbrief/client/src/App.tsx", currentExports, nextExports);
      if (invalidateMessage) import.meta.hot.invalidate(invalidateMessage);
    });
  });
}

//# sourceMappingURL=data:application/json;base64,eyJ2ZXJzaW9uIjozLCJtYXBwaW5ncyI6IkFBcUI2Qzs7Ozs7Ozs7Ozs7Ozs7OztBQXJCN0MsU0FBU0EsZUFBZUMsUUFBUUMsYUFBYTtBQUM3QyxTQUFTQyxzQkFBc0I7QUFDL0IsU0FBU0MscUJBQXFCO0FBQzlCLFNBQVNDLGNBQWM7QUFDdkI7QUFBQSxFQUNFQztBQUFBQSxFQUNBQztBQUFBQSxFQUNBQztBQUFBQSxFQUNBQztBQUFBQSxFQUNBQztBQUFBQSxFQUNBQztBQUFBQSxFQUNBQztBQUFBQSxPQUNLO0FBRVAsU0FBU0MsTUFBTTtBQUNiLFNBQ0UsdUJBQUMsa0JBQ0MsaUNBQUMsaUJBQ0MsaUNBQUMsaUJBQ0MsaUNBQUMsVUFFQztBQUFBLDJCQUFDLFNBQU0sTUFBSyxLQUFJLFNBQVMsdUJBQUMsVUFBTyxpQ0FBQyxpQkFBRDtBQUFBO0FBQUE7QUFBQTtBQUFBLFdBQVksS0FBcEI7QUFBQTtBQUFBO0FBQUE7QUFBQSxXQUF1QixLQUFoRDtBQUFBO0FBQUE7QUFBQTtBQUFBLFdBQTBEO0FBQUEsSUFDMUQsdUJBQUMsU0FBTSxNQUFLLGFBQVksU0FBUyx1QkFBQyxVQUFPLGlDQUFDLGtCQUFEO0FBQUE7QUFBQTtBQUFBO0FBQUEsV0FBYSxLQUFyQjtBQUFBO0FBQUE7QUFBQTtBQUFBLFdBQXdCLEtBQXpEO0FBQUE7QUFBQTtBQUFBO0FBQUEsV0FBbUU7QUFBQSxJQUNuRSx1QkFBQyxTQUFNLE1BQUssWUFBVyxTQUFTLHVCQUFDLFVBQU8saUNBQUMsaUJBQUQ7QUFBQTtBQUFBO0FBQUE7QUFBQSxXQUFZLEtBQXBCO0FBQUE7QUFBQTtBQUFBO0FBQUEsV0FBdUIsS0FBdkQ7QUFBQTtBQUFBO0FBQUE7QUFBQSxXQUFpRTtBQUFBLElBQ2pFLHVCQUFDLFNBQU0sTUFBSyxVQUFTLFNBQVMsdUJBQUMsVUFBTyxpQ0FBQyxlQUFEO0FBQUE7QUFBQTtBQUFBO0FBQUEsV0FBVSxLQUFsQjtBQUFBO0FBQUE7QUFBQTtBQUFBLFdBQXFCLEtBQW5EO0FBQUE7QUFBQTtBQUFBO0FBQUEsV0FBNkQ7QUFBQSxJQUM3RCx1QkFBQyxTQUFNLE1BQUssU0FBUSxTQUFTLHVCQUFDLFVBQU8saUNBQUMsY0FBRDtBQUFBO0FBQUE7QUFBQTtBQUFBLFdBQVMsS0FBakI7QUFBQTtBQUFBO0FBQUE7QUFBQSxXQUFvQixLQUFqRDtBQUFBO0FBQUE7QUFBQTtBQUFBLFdBQTJEO0FBQUEsSUFDM0QsdUJBQUMsU0FBTSxNQUFLLGFBQVksU0FBUyx1QkFBQyxVQUFPLGlDQUFDLGNBQUQ7QUFBQTtBQUFBO0FBQUE7QUFBQSxXQUFTLEtBQWpCO0FBQUE7QUFBQTtBQUFBO0FBQUEsV0FBb0IsS0FBckQ7QUFBQTtBQUFBO0FBQUE7QUFBQSxXQUErRDtBQUFBLElBQy9ELHVCQUFDLFNBQU0sTUFBSyxZQUFXLFNBQVMsdUJBQUMsVUFBTyxpQ0FBQyxpQkFBRDtBQUFBO0FBQUE7QUFBQTtBQUFBLFdBQVksS0FBcEI7QUFBQTtBQUFBO0FBQUE7QUFBQSxXQUF1QixLQUF2RDtBQUFBO0FBQUE7QUFBQTtBQUFBLFdBQWlFO0FBQUEsSUFHakUsdUJBQUMsU0FBTSxNQUFLLFFBQU8sU0FBUyx1QkFBQyxhQUFEO0FBQUE7QUFBQTtBQUFBO0FBQUEsV0FBUSxLQUFwQztBQUFBO0FBQUE7QUFBQTtBQUFBLFdBQXdDO0FBQUEsT0FYMUM7QUFBQTtBQUFBO0FBQUE7QUFBQSxTQVlBLEtBYkY7QUFBQTtBQUFBO0FBQUE7QUFBQSxTQWNBLEtBZkY7QUFBQTtBQUFBO0FBQUE7QUFBQSxTQWdCQSxLQWpCRjtBQUFBO0FBQUE7QUFBQTtBQUFBLFNBa0JBO0FBRUo7QUFBQ0MsS0F0QlFEO0FBd0JULGVBQWVBO0FBQUksSUFBQUM7QUFBQUMsYUFBQUQsSUFBQSIsIm5hbWVzIjpbIkJyb3dzZXJSb3V0ZXIiLCJSb3V0ZXMiLCJSb3V0ZSIsIkhlbG1ldFByb3ZpZGVyIiwiVGhlbWVQcm92aWRlciIsIkxheW91dCIsIkxhbmRpbmdQYWdlIiwiRmVhdHVyZXNQYWdlIiwiUHJpY2luZ1BhZ2UiLCJBYm91dFBhZ2UiLCJCbG9nUGFnZSIsIkNvbnRhY3RQYWdlIiwiQXBwUGFnZSIsIkFwcCIsIl9jIiwiJFJlZnJlc2hSZWckIl0sImlnbm9yZUxpc3QiOltdLCJzb3VyY2VzIjpbIkFwcC50c3giXSwic291cmNlc0NvbnRlbnQiOlsiaW1wb3J0IHsgQnJvd3NlclJvdXRlciwgUm91dGVzLCBSb3V0ZSB9IGZyb20gJ3JlYWN0LXJvdXRlci1kb20nO1xyXG5pbXBvcnQgeyBIZWxtZXRQcm92aWRlciB9IGZyb20gJ3JlYWN0LWhlbG1ldC1hc3luYyc7XHJcbmltcG9ydCB7IFRoZW1lUHJvdmlkZXIgfSBmcm9tICcuL2NvbnRleHQvVGhlbWVDb250ZXh0JztcclxuaW1wb3J0IHsgTGF5b3V0IH0gZnJvbSAnLi9jb21wb25lbnRzL2xheW91dC9MYXlvdXQnO1xyXG5pbXBvcnQge1xyXG4gIExhbmRpbmdQYWdlLFxyXG4gIEZlYXR1cmVzUGFnZSxcclxuICBQcmljaW5nUGFnZSxcclxuICBBYm91dFBhZ2UsXHJcbiAgQmxvZ1BhZ2UsXHJcbiAgQ29udGFjdFBhZ2UsXHJcbiAgQXBwUGFnZVxyXG59IGZyb20gJy4vcGFnZXMnO1xyXG5cclxuZnVuY3Rpb24gQXBwKCkge1xyXG4gIHJldHVybiAoXHJcbiAgICA8SGVsbWV0UHJvdmlkZXI+XHJcbiAgICAgIDxUaGVtZVByb3ZpZGVyPlxyXG4gICAgICAgIDxCcm93c2VyUm91dGVyPlxyXG4gICAgICAgICAgPFJvdXRlcz5cclxuICAgICAgICAgICAgey8qIE1hcmtldGluZyBwYWdlcyB3aXRoIGxheW91dCAqL31cclxuICAgICAgICAgICAgPFJvdXRlIHBhdGg9XCIvXCIgZWxlbWVudD17PExheW91dD48TGFuZGluZ1BhZ2UgLz48L0xheW91dD59IC8+XHJcbiAgICAgICAgICAgIDxSb3V0ZSBwYXRoPVwiL2ZlYXR1cmVzXCIgZWxlbWVudD17PExheW91dD48RmVhdHVyZXNQYWdlIC8+PC9MYXlvdXQ+fSAvPlxyXG4gICAgICAgICAgICA8Um91dGUgcGF0aD1cIi9wcmljaW5nXCIgZWxlbWVudD17PExheW91dD48UHJpY2luZ1BhZ2UgLz48L0xheW91dD59IC8+XHJcbiAgICAgICAgICAgIDxSb3V0ZSBwYXRoPVwiL2Fib3V0XCIgZWxlbWVudD17PExheW91dD48QWJvdXRQYWdlIC8+PC9MYXlvdXQ+fSAvPlxyXG4gICAgICAgICAgICA8Um91dGUgcGF0aD1cIi9ibG9nXCIgZWxlbWVudD17PExheW91dD48QmxvZ1BhZ2UgLz48L0xheW91dD59IC8+XHJcbiAgICAgICAgICAgIDxSb3V0ZSBwYXRoPVwiL2Jsb2cvOmlkXCIgZWxlbWVudD17PExheW91dD48QmxvZ1BhZ2UgLz48L0xheW91dD59IC8+XHJcbiAgICAgICAgICAgIDxSb3V0ZSBwYXRoPVwiL2NvbnRhY3RcIiBlbGVtZW50PXs8TGF5b3V0PjxDb250YWN0UGFnZSAvPjwvTGF5b3V0Pn0gLz5cclxuICAgICAgICAgICAgXHJcbiAgICAgICAgICAgIHsvKiBBcHAgLSBubyBsYXlvdXQsIGZ1bGwgc2NyZWVuICovfVxyXG4gICAgICAgICAgICA8Um91dGUgcGF0aD1cIi9hcHBcIiBlbGVtZW50PXs8QXBwUGFnZSAvPn0gLz5cclxuICAgICAgICAgIDwvUm91dGVzPlxyXG4gICAgICAgIDwvQnJvd3NlclJvdXRlcj5cclxuICAgICAgPC9UaGVtZVByb3ZpZGVyPlxyXG4gICAgPC9IZWxtZXRQcm92aWRlcj5cclxuICApO1xyXG59XHJcblxyXG5leHBvcnQgZGVmYXVsdCBBcHA7XHJcbiJdLCJmaWxlIjoiRDovcmVwb3MvYnVpbGRicmllZi9jbGllbnQvc3JjL0FwcC50c3gifQ==