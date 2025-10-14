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
        # Model/artifact fields
        self.model = None
        self.features: List[str] = []
        self.meta: Dict[str, Any] = {}
        self.threshold: float = 0.5
        # Optional calibration (Platt)
        self._calib_method: Optional[str] = None
        self._calib_a: Optional[float] = None
        self._calib_b: Optional[float] = None
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

    def _load_model(self, model_path: Optional[str] = None) -> None:
        """Load trained artifact if available; set robust defaults otherwise."""
        path = self._resolve_model_path(model_path)
        self.model = None
        self.features = []
        self.meta = {}
        self.threshold = 0.5
        self._calib_method = None
        self._calib_a = None
        self._calib_b = None
        try:
            if os.path.exists(path):
                with open(path, "rb") as f:
                    artifact = pickle.load(f)
                if isinstance(artifact, dict):
                    self.model = artifact.get("model") or artifact.get("clf") or artifact.get("estimator")
                    self.features = artifact.get("features") or artifact.get("feature_names") or []
                    self.meta = artifact.get("meta") or artifact.get("metadata") or {}
                    if "threshold" in artifact:
                        self.threshold = float(artifact.get("threshold", self.threshold))
                    elif isinstance(self.meta, dict) and "threshold" in self.meta:
                        # threshold persisted only inside meta
                        try:
                            self.threshold = float(self.meta.get("threshold"))
                        except Exception:
                            pass
                    calib = artifact.get("calibration") or {}
                    self._calib_method = calib.get("method")
                    self._calib_a = calib.get("a")
                    self._calib_b = calib.get("b")
                else:
                    # Fallback if the pickled object is the estimator itself
                    self.model = artifact
                    self.features = []
                    self.meta = {}
                    self.threshold = 0.5
            else:
                # No model available; keep defaults
                pass
        except Exception:
            # If artifact load fails, keep safe defaults
            self.model = None
            self.features = []
            self.meta = {}
            self.threshold = 0.5

        # Provide a sensible default feature list if not present (keeps API usable)
        if not self.features:
            self.features = [
                "price_ma7","price_ma14","price_ma30","price_ma60","price_ma90",
                "price_std14","price_std30","price_std60","price_std90",
                "price_ema7","price_ema30","price_z_ma30","price_z_ma90",
                "price_slope7","price_slope30","price_slope90",
                "price_var7","price_var30","price_var90",
                "price_max30","price_min30","price_max90","price_min90",
                "disc_freq7","disc_freq14","disc_freq30","disc_freq60","disc_freq90",
                "disc_mean30","disc_mean90","disc_max30","disc_max90",
                "disc_strong_freq30","disc_strong_freq90",
                "avg_gap_disc90","days_since_max_disc90",
                "price_ma7_over_30","days_since_last_disc",
                "type_encoded","years_since_release",
                "season_winter","season_spring","season_summer","season_fall",
                "sale_winter","sale_summer","sale_autumn","sale_lunar_new_year",
                "sale_halloween","sale_spring","sale_black_friday",
            ]

    def reload(self) -> None:
        """Reload artifact and clear cache."""
        self._load_model(None)
        self._cache.clear()

    # ---------------------- DB helpers ----------------------
    def _fetch_game_and_prices(self, appid: int) -> Dict[str, Any]:
        try:
            conn = mysql.connector.connect(**self.mysql_config)
            cur = conn.cursor(dictionary=True)
            cur.execute("SELECT * FROM games WHERE appid = %s", (appid,))
            game = cur.fetchone()
            if not game:
                cur.close(); conn.close()
                return {"error": "Game not found"}
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
            cur.close(); conn.close()
            if not rows:
                return {"error": "No price history"}
            df = pd.DataFrame(rows)
            # normalize dtypes
            df["date"] = pd.to_datetime(df["date"], errors="coerce")
            df = df.dropna(subset=["date"])  # drop invalid dates
            df = df.sort_values("date")
            df["finalprice"] = pd.to_numeric(df["finalprice"], errors="coerce")
            df["discount"] = pd.to_numeric(df["discount"], errors="coerce")
            df = df.dropna(subset=["finalprice"])  # require price
            if len(df) < 7:
                return {"error": "Insufficient data for features"}
            return {"game": game, "prices": df.reset_index(drop=True)}
        except Exception as e:
            return {"error": str(e)}

    # ---------------------- Feature builder ----------------------
    def _build_features_from_window(self, game: Dict[str, Any], df: pd.DataFrame) -> Optional[Dict[str, float]]:
        if df is None or df.empty:
            return None
        # ensure sorted ascending
        df = df.sort_values("date").reset_index(drop=True)
        # windows
        last7 = df.tail(7)
        last14 = df.tail(14)
        last30 = df.tail(30)
        last60 = df.tail(60)
        last90 = df.tail(90)

        def safe_mean(s: pd.Series) -> float:
            return float(pd.to_numeric(s, errors="coerce").dropna().mean()) if len(s) else 0.0

        def safe_std(s: pd.Series) -> float:
            return float(pd.to_numeric(s, errors="coerce").dropna().std()) if len(s) else 0.0

        def safe_var(s: pd.Series) -> float:
            return float(pd.to_numeric(s, errors="coerce").dropna().var()) if len(s) else 0.0

        def ema(s: pd.Series, span: int) -> float:
            s = pd.to_numeric(s, errors="coerce").dropna()
            return float(s.ewm(span=span, adjust=False).mean().iloc[-1]) if len(s) else 0.0

        def slope(s: pd.Series) -> float:
            arr = pd.to_numeric(s, errors="coerce").dropna().values
            n = len(arr)
            if n < 2:
                return 0.0
            x = np.arange(n)
            try:
                m = np.polyfit(x, arr, 1)[0]
                return float(m)
            except Exception:
                return 0.0

        # discount flags
        disc_bin = (pd.to_numeric(df["discount"], errors="coerce").fillna(0.0) > 0.0).astype(int)
        disc_last7 = disc_bin.tail(7)
        disc_last14 = disc_bin.tail(14)
        disc_last30 = disc_bin.tail(30)
        disc_last60 = disc_bin.tail(60)
        disc_last90 = disc_bin.tail(90)

        price_ma7 = safe_mean(last7["finalprice"])
        price_ma14 = safe_mean(last14["finalprice"])
        price_ma30 = safe_mean(last30["finalprice"])
        price_ma60 = safe_mean(last60["finalprice"])
        price_ma90 = safe_mean(last90["finalprice"])

        price_std14 = safe_std(last14["finalprice"]) 
        price_std30 = safe_std(last30["finalprice"]) 
        price_std60 = safe_std(last60["finalprice"]) 
        price_std90 = safe_std(last90["finalprice"]) 

        price_ema7 = ema(df["finalprice"], 7)
        price_ema30 = ema(df["finalprice"], 30)

        price_z_ma30 = (df["finalprice"].iloc[-1] - price_ma30) / (price_std30 if price_std30 not in (0, 0.0) else 1.0)
        price_z_ma90 = (df["finalprice"].iloc[-1] - price_ma90) / (price_std90 if price_std90 not in (0, 0.0) else 1.0)

        price_slope7 = slope(last7["finalprice"]) 
        price_slope30 = slope(last30["finalprice"]) 
        price_slope90 = slope(last90["finalprice"]) 

        price_var7 = safe_var(last7["finalprice"]) 
        price_var30 = safe_var(last30["finalprice"]) 
        price_var90 = safe_var(last90["finalprice"]) 

        price_max30 = float(pd.to_numeric(last30["finalprice"], errors="coerce").dropna().max()) if len(last30) else 0.0
        price_min30 = float(pd.to_numeric(last30["finalprice"], errors="coerce").dropna().min()) if len(last30) else 0.0
        price_max90 = float(pd.to_numeric(last90["finalprice"], errors="coerce").dropna().max()) if len(last90) else 0.0
        price_min90 = float(pd.to_numeric(last90["finalprice"], errors="coerce").dropna().min()) if len(last90) else 0.0

        # discounts stats
        disc_vals = pd.to_numeric(df["discount"], errors="coerce").fillna(0.0)
        disc_mean30 = float(pd.to_numeric(last30["discount"], errors="coerce").dropna().mean()) if len(last30) else 0.0
        disc_mean90 = float(pd.to_numeric(last90["discount"], errors="coerce").dropna().mean()) if len(last90) else 0.0
        disc_max30 = float(pd.to_numeric(last30["discount"], errors="coerce").dropna().max()) if len(last30) else 0.0
        disc_max90 = float(pd.to_numeric(last90["discount"], errors="coerce").dropna().max()) if len(last90) else 0.0

        # frequencies
        disc_freq7 = float(disc_last7.mean()) if len(disc_last7) else 0.0
        disc_freq14 = float(disc_last14.mean()) if len(disc_last14) else 0.0
        disc_freq30 = float(disc_last30.mean()) if len(disc_last30) else 0.0
        disc_freq60 = float(disc_last60.mean()) if len(disc_last60) else 0.0
        disc_freq90 = float(disc_last90.mean()) if len(disc_last90) else 0.0

        # strong discount freq (>= 40)
        strong_last30 = pd.to_numeric(last30["discount"], errors="coerce").fillna(0.0) >= 40.0
        strong_last90 = pd.to_numeric(last90["discount"], errors="coerce").fillna(0.0) >= 40.0
        disc_strong_freq30 = float(strong_last30.mean()) if len(last30) else 0.0
        disc_strong_freq90 = float(strong_last90.mean()) if len(last90) else 0.0

        # gaps between discounts in last90
        idx_disc = np.where(disc_last90.values == 1)[0]
        if len(idx_disc) >= 2:
            gaps = np.diff(idx_disc)
            avg_gap_disc90 = float(np.mean(gaps))
        else:
            avg_gap_disc90 = float(0.0)

        # days since max discount within last90
        as_of_date = pd.Timestamp(df.iloc[-1]["date"]).normalize()
        last90_df = last90.copy()
        if len(last90_df) > 0 and pd.to_numeric(last90_df["discount"], errors="coerce").dropna().shape[0] > 0:
            max_disc_idx = pd.to_numeric(last90_df["discount"], errors="coerce").astype(float).idxmax()
            d_max = pd.Timestamp(df.loc[max_disc_idx, "date"]).normalize()
            days_since_max_disc90 = float((as_of_date - d_max).days)
        else:
            days_since_max_disc90 = float(0.0)

        price_ma7_over_30 = (price_ma7 / price_ma30) if price_ma30 not in (0, 0.0) else 0.0

        # days since last discount (entire history)
        if (disc_bin == 1).any():
            last_disc_pos = disc_bin[disc_bin == 1].index.max()
            last_disc_date = pd.Timestamp(df.loc[last_disc_pos, "date"]).normalize()
            days_since_last_disc = float((as_of_date - last_disc_date).days)
        else:
            days_since_last_disc = float(0.0)

        # metadata features
        type_map = {"game": 1, "dlc": 2, "demo": 3, "unknown": 0}
        type_str = str(game.get("type") or "unknown").lower()
        type_encoded = float(type_map.get(type_str, 0))

        years_since_release = 0.0
        try:
            rel = game.get("releasedate")
            rel_ts = pd.to_datetime(rel, errors="coerce")
            if pd.notna(rel_ts):
                years_since_release = max(0.0, float((as_of_date - rel_ts).days) / 365.25)
        except Exception:
            years_since_release = 0.0

        m = int(as_of_date.month)
        day = int(as_of_date.day)
        season_winter = 1.0 if m in (12, 1, 2) else 0.0
        season_spring = 1.0 if m in (3, 4, 5) else 0.0
        season_summer = 1.0 if m in (6, 7, 8) else 0.0
        season_fall = 1.0 if m in (9, 10, 11) else 0.0
        # big sale season flags (heurística)
        sale_winter = 1.0 if ((m == 12 and day >= 15) or (m == 1 and day <= 7)) else 0.0
        sale_summer = 1.0 if ((m == 6 and day >= 20) or (m == 7 and day <= 10)) else 0.0
        sale_autumn = 1.0 if (m == 11 and 20 <= day <= 30) else 0.0
        # optional additional flags used in frontend descriptions
        sale_lunar_new_year = 1.0 if (m in (1, 2) and day <= 15) else 0.0
        sale_halloween = 1.0 if (m == 10 and 25 <= day <= 31) else 0.0
        sale_spring = 1.0 if (m in (3, 4) and day <= 15) else 0.0
        sale_black_friday = 1.0 if (m == 11 and 20 <= day <= 30) else 0.0

        feats = {
            "price_ma7": price_ma7,
            "price_ma14": price_ma14,
            "price_ma30": price_ma30,
            "price_ma60": price_ma60,
            "price_ma90": price_ma90,
            "price_std14": price_std14,
            "price_std30": price_std30,
            "price_std60": price_std60,
            "price_std90": price_std90,
            "price_ema7": price_ema7,
            "price_ema30": price_ema30,
            "price_z_ma30": float(price_z_ma30),
            "price_z_ma90": float(price_z_ma90),
            "price_slope7": price_slope7,
            "price_slope30": price_slope30,
            "price_slope90": price_slope90,
            "price_var7": price_var7,
            "price_var30": price_var30,
            "price_var90": price_var90,
            "price_max30": price_max30,
            "price_min30": price_min30,
            "price_max90": price_max90,
            "price_min90": price_min90,
            "disc_freq7": disc_freq7,
            "disc_freq14": disc_freq14,
            "disc_freq30": disc_freq30,
            "disc_freq60": disc_freq60,
            "disc_freq90": disc_freq90,
            "disc_mean30": disc_mean30,
            "disc_mean90": disc_mean90,
            "disc_max30": disc_max30,
            "disc_max90": disc_max90,
            "disc_strong_freq30": disc_strong_freq30,
            "disc_strong_freq90": disc_strong_freq90,
            "avg_gap_disc90": avg_gap_disc90,
            "days_since_max_disc90": days_since_max_disc90,
            "price_ma7_over_30": float(price_ma7_over_30),
            "days_since_last_disc": float(days_since_last_disc),
            "type_encoded": type_encoded,
            "years_since_release": float(years_since_release),
            "season_winter": season_winter,
            "season_spring": season_spring,
            "season_summer": season_summer,
            "season_fall": season_fall,
            "sale_winter": sale_winter,
            "sale_summer": sale_summer,
            "sale_autumn": sale_autumn,
            "sale_lunar_new_year": sale_lunar_new_year,
            "sale_halloween": sale_halloween,
            "sale_spring": sale_spring,
            "sale_black_friday": sale_black_friday,
        }

        # align/order by model features, filling missing with 0.0
        ordered = {name: float(feats.get(name, 0.0)) for name in self.features}
        return ordered

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

        X = np.array([[feats.get(f, 0.0) for f in self.features]], dtype=float)
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

    # ---------------------- Inspect (features vector) ----------------------
    def inspect(self, appid: int) -> Dict[str, Any]:
        """Return ordered feature vector for given appid; never raise, return error key."""
        try:
            if self.model is None:
                return {"error": "Model not loaded"}
            data = self._fetch_game_and_prices(appid)
            if "error" in data:
                return data
            feats = self._build_features_from_window(data["game"], data["prices"])
            if feats is None:
                return {"error": "Insufficient data for features"}
            # feats already ordered by self.features; ensure numeric + finite
            cleaned: Dict[str, float] = {}
            for name in self.features:
                val = feats.get(name, 0.0)
                try:
                    v = float(val)
                except Exception:
                    v = 0.0
                if not np.isfinite(v):
                    v = 0.0
                cleaned[name] = v
            as_of = None
            prices_df = data.get("prices")
            if prices_df is not None and len(prices_df) > 0:
                try:
                    as_of = str(prices_df.iloc[-1]["date"])[:10]
                except Exception:
                    as_of = None
            return {
                "appid": appid,
                "features": cleaned,
                "feature_names": self.features,
                "as_of_date": as_of,
                "n_price_rows": int(len(prices_df)) if prices_df is not None else 0,
            }
        except Exception as e:
            return {"error": str(e)}
