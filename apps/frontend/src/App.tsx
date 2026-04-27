import { Navigate, Route, Routes } from "react-router-dom";

import { Layout } from "./components/Layout";
import { AdminPage } from "./pages/AdminPage";
import { MyCredentialsPage } from "./pages/MyCredentialsPage";
import { PublicPage } from "./pages/PublicPage";


export default function App() {
  return (
    <Routes>
      <Route element={<Layout />} path="/">
        <Route element={<PublicPage />} index />
        <Route element={<MyCredentialsPage />} path="my" />
        <Route element={<AdminPage />} path="admin" />
        <Route element={<Navigate replace to="/" />} path="*" />
      </Route>
    </Routes>
  );
}

