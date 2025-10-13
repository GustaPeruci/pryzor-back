"""
Discount Forecast Service
Loads the 30-day discount forecast model artifact and serves predictions
based on MySQL price history for a given appid.
"""

from __future__ import annotations

import os
import pickle
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import mysql.connector
import numpy as np
import pandas as pd


class DiscountForecastService:
    def __init__(self, mysql_config: Dict[str, Any], model_path: Optional[str] = None):
        self.mysql_config = mysql_config
        self.model = None
        self.features: List[str] = []
        self.meta: Dict[str, Any] = {}
        self.threshold: float = 0.5
        # simple in-memory cache: appid -> (timestamp, result)
        self._cache: Dict[int, Tuple[pd.Timestamp, Dict[str, Any]]] = {}
        self._cache_ttl_min = float(os.getenv("DISCOUNT30D_CACHE_MIN", "10"))  # minutes
        self._load_model(model_path)

    def _resolve_model_path(self, model_path: Optional[str]) -> str:
        if model_path and os.path.exists(model_path):
            return os.path.abspath(model_path)

        env_path = os.getenv("MODEL_PATH")
        if env_path:
            if os.path.isdir(env_path):
                candidate = os.path.join(env_path, "discount_30d_model.pkl")
            else:
                candidate = env_path
            if os.path.exists(candidate):
                return os.path.abspath(candidate)

        # default: repo_root/ml_model/trained_models/discount_30d_model.pkl
        here = os.path.dirname(__file__)
        repo_root = os.path.abspath(os.path.join(here, "..", "..", ".."))
        default_path = os.path.join(repo_root, "ml_model", "trained_models", "discount_30d_model.pkl")
        return default_path

    def _load_model(self, model_path: Optional[str]) -> None:
        path = self._resolve_model_path(model_path)
        if not os.path.exists(path):
            raise FileNotFoundError(f"Model artifact not found: {path}")
        with open(path, "rb") as f:
            art = pickle.load(f)
        self.model = art["model"]
        self.features = art.get("features", [])
        self.meta = art.get("metadata", {})
        # default threshold from artifact metadata
        self.threshold = float(self.meta.get("threshold", 0.5))
        # calibration params (Platt)
        calib = self.meta.get("calibration", {}) or {}
        self._calib_method = calib.get("method")
        self._calib_a = calib.get("a")
        self._calib_b = calib.get("b")
        # optional override via env
        env_thr = os.getenv("DISCOUNT30D_THRESHOLD")
        if env_thr:
            try:
                self.threshold = float(env_thr)
            except ValueError:
                pass

    def reload(self, model_path: Optional[str] = None) -> None:
        """Public method to reload model artifact and clear cache."""
        self._load_model(model_path)
        self._cache.clear()

    def _conn(self):
        return mysql.connector.connect(**self.mysql_config)

    def _fetch_game_and_prices(self, appid: int) -> Dict[str, Any]:
        with self._conn() as conn:
            cur = conn.cursor(dictionary=True)
            cur.execute("SELECT name, type, releasedate FROM games WHERE appid = %s", (appid,))
            game = cur.fetchone()
            if not game:
                return {"error": "Game not found"}

            # Fetch last 120 records to be safe
            cur.execute(
                """
                SELECT date, finalprice, discount
                FROM price_history
                WHERE appid = %s AND finalprice IS NOT NULL
                ORDER BY date ASC
                """,
                (appid,),
            )
            rows = cur.fetchall()
        if not rows or len(rows) < 7:
            return {"error": "Insufficient price history"}
        df = pd.DataFrame(rows)
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df["finalprice"] = pd.to_numeric(df["finalprice"], errors="coerce")
        df["discount"] = pd.to_numeric(df["discount"], errors="coerce").fillna(0)
        df = df.dropna(subset=["date", "finalprice"]).sort_values("date").reset_index(drop=True)
        return {"game": game, "prices": df}

    def _build_features_from_window(self, game: Dict[str, Any], df: pd.DataFrame) -> Optional[Dict[str, float]]:
        # Use last available record as reference time
        if len(df) < 7:
            return None
        # compute from last 30/7 rows if available
        last7 = df.tail(7)
        last30 = df.tail(30)
        last90 = df.tail(90)
        disc_bin = (df["discount"] >= float(self.meta.get("discount_threshold", 20.0))).astype(int)
        disc_last7 = disc_bin.tail(7)
        disc_last30 = disc_bin.tail(30)
        disc_last90 = disc_bin.tail(90)

        price_ma7 = last7["finalprice"].mean()
        price_ma30 = last30["finalprice"].mean()
        price_std30 = last30["finalprice"].std()
        price_ma90 = last90["finalprice"].mean()
        price_std90 = last90["finalprice"].std()
        disc_freq7 = float(disc_last7.mean()) if len(disc_last7) > 0 else 0.0
        disc_freq30 = float(disc_last30.mean()) if len(disc_last30) > 0 else 0.0
        disc_freq90 = float(disc_last90.mean()) if len(disc_last90) > 0 else 0.0
        price_ma7_over_30 = (float(price_ma7) / float(price_ma30)) if (pd.notna(price_ma7) and pd.notna(price_ma30) and price_ma30 not in (0, 0.0)) else 0.0

        # days since last discount
        last_disc_date = df.loc[disc_bin[disc_bin == 1].index.max(), "date"] if (disc_bin == 1).any() else pd.NaT
        as_of_date = df.iloc[-1]["date"]
        if pd.isna(last_disc_date):
            days_since_last_disc = np.nan
        else:
            days_since_last_disc = float((as_of_date - last_disc_date).days)

        # metadata features
        type_map = {"game": 1, "dlc": 2, "demo": 3, "unknown": 0}
        type_str = str(game.get("type") or "unknown").lower()
        type_encoded = type_map.get(type_str, 0)

        rel = game.get("releasedate")
        years_since_release = np.nan
        try:
            rel_ts = pd.to_datetime(rel, errors="coerce")
            if pd.notna(rel_ts):
                years_since_release = max(0.0, float((as_of_date - rel_ts).days) / 365.25)
        except Exception:
            pass

        m = int(pd.Timestamp(as_of_date).month)
        season_winter = 1 if m in (12, 1, 2) else 0
        season_spring = 1 if m in (3, 4, 5) else 0
        season_summer = 1 if m in (6, 7, 8) else 0
        season_fall = 1 if m in (9, 10, 11) else 0
        # big sale season flags (heurística compatível com treino)
        day = int(pd.Timestamp(as_of_date).day)
        sale_winter = 1 if (m == 12 and day >= 15) or (m == 1 and day <= 7) else 0
        sale_summer = 1 if (m == 6 and day >= 20) or (m == 7 and day <= 10) else 0
        sale_autumn = 1 if (m == 11 and 20 <= day <= 30) else 0

        feats = {
            "price_ma7": float(price_ma7) if pd.notna(price_ma7) else 0.0,
            "price_ma30": float(price_ma30) if pd.notna(price_ma30) else 0.0,
            "price_std30": float(price_std30) if pd.notna(price_std30) else 0.0,
            "price_ma90": float(price_ma90) if pd.notna(price_ma90) else 0.0,
            "price_std90": float(price_std90) if pd.notna(price_std90) else 0.0,
            "disc_freq7": float(disc_freq7),
            "disc_freq30": float(disc_freq30),
            "disc_freq90": float(disc_freq90),
            "price_ma7_over_30": float(price_ma7_over_30),
            "days_since_last_disc": float(days_since_last_disc) if not pd.isna(days_since_last_disc) else 0.0,
            "type_encoded": float(type_encoded),
            "years_since_release": float(years_since_release) if not pd.isna(years_since_release) else 0.0,
            "season_winter": float(season_winter),
            "season_spring": float(season_spring),
            "season_summer": float(season_summer),
            "season_fall": float(season_fall),
            "sale_winter": float(sale_winter),
            "sale_summer": float(sale_summer),
            "sale_autumn": float(sale_autumn),
        }
        return {k: feats[k] for k in self.features if k in feats}

    def predict(self, appid: int) -> Dict[str, Any]:
        if self.model is None:
            return {"error": "Model not loaded"}

        # cache hit
        now = pd.Timestamp.utcnow()
        if appid in self._cache:
            ts, val = self._cache[appid]
            if (now - ts).total_seconds() <= self._cache_ttl_min * 60:
                return val

        data = self._fetch_game_and_prices(appid)
        if "error" in data:
            return data
        game, df = data["game"], data["prices"]
        feats = self._build_features_from_window(game, df)
        if feats is None:
            return {"error": "Insufficient data for features"}

        X = np.array([[feats[f] for f in self.features]], dtype=float)
        if hasattr(self.model, "predict_proba"):
            proba_raw = float(self.model.predict_proba(X)[0, 1])
        else:
            score = float(self.model.decision_function(X)[0])
            # map decision score to [0,1] via logistic
            proba_raw = 1.0 / (1.0 + np.exp(-score))
        # apply Platt calibration if available
        if self._calib_method == "platt" and self._calib_a is not None and self._calib_b is not None:
            pr = max(1e-6, min(1 - 1e-6, proba_raw))
            z = float(self._calib_a) * pr + float(self._calib_b)
            proba = 1.0 / (1.0 + np.exp(-z))
        else:
            proba = proba_raw
        label = int(proba >= self.threshold)

        result = {
            "appid": appid,
            "game_name": game["name"],
            "as_of_date": str(df.iloc[-1]["date"].date()),
            "prob_discount_30d": proba,
            "will_discount_30d": bool(label),
            "threshold": self.threshold,
            "lookback_days": int(self.meta.get("lookback_days", 30)),
            "horizon_days": int(self.meta.get("horizon_days", 30)),
            "discount_threshold": float(self.meta.get("discount_threshold", 20.0)),
            "features_used": self.features,
            "model_info": {
                "created_at": self.meta.get("created_at"),
            },
        }
        # store cache
        self._cache[appid] = (now, result)
        return result

    def predict_batch(self, appids: List[int]) -> Dict[int, Dict[str, Any]]:
        out: Dict[int, Dict[str, Any]] = {}
        for aid in appids:
            try:
                out[aid] = self.predict(aid)
            except Exception as e:
                out[aid] = {"error": str(e)}
        return out
