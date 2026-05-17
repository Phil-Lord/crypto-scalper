from dataclasses import asdict

from sqlalchemy import text

from data_system.clients import SQLAlchemyClient
from data_system.models import OosWindowAggregate, OutOfSampleEvaluation
from .out_of_sample_evaluation_repository import OutOfSampleEvaluationRepository


class SQLAlchemyOutOfSampleEvaluationRepository(OutOfSampleEvaluationRepository):
    def __init__(self, client: SQLAlchemyClient) -> None:
        self.client = client

    def add(self, evaluations: list[OutOfSampleEvaluation]) -> None:
        if not evaluations:
            return

        with self.client.session() as session:
            records = [asdict(e) for e in evaluations]

            stmt = text("""
                INSERT OR REPLACE INTO out_of_sample_evaluation
                (study_name, trial_number, start_timestamp, end_timestamp, geo_mean_balance_ratio)
                VALUES (:study_name, :trial_number, :start_timestamp, :end_timestamp, :geo_mean_balance_ratio)
            """)

            session.execute(stmt, records)

    def get_evaluated_trial_numbers(self, study_name: str, start: float, end: float) -> set[int]:
        with self.client.session() as session:
            query = text("""
                SELECT trial_number FROM out_of_sample_evaluation
                WHERE study_name = :study_name
                  AND start_timestamp = :start
                  AND end_timestamp = :end
            """)

            result = session.execute(query, {
                "study_name": study_name,
                "start": start,
                "end": end
            })
            rows = result.fetchall()

            return {row[0] for row in rows}

    def get(self, study_name: str, start: float, end: float) -> list[OutOfSampleEvaluation]:
        with self.client.session() as session:
            query = text("""
                SELECT study_name, trial_number, start_timestamp, end_timestamp, geo_mean_balance_ratio
                FROM out_of_sample_evaluation
                WHERE study_name = :study_name
                  AND start_timestamp = :start
                  AND end_timestamp = :end
                ORDER BY trial_number
            """)
            result = session.execute(query, {
                "study_name": study_name,
                "start": start,
                "end": end
            })
            return [
                OutOfSampleEvaluation(
                    study_name=row[0],
                    trial_number=row[1],
                    start_timestamp=row[2],
                    end_timestamp=row[3],
                    geo_mean_balance_ratio=row[4],
                )
                for row in result.fetchall()
            ]

    def aggregate_windows(
        self, study_name: str, floor: float, drawdown_limit: float
    ) -> list[OosWindowAggregate]:
        with self.client.session() as session:
            query = text("""
                SELECT
                    start_timestamp,
                    end_timestamp,
                    MAX(oos_balance_ratio) AS best_oos,
                    SUM(CASE
                        WHEN oos_balance_ratio >= :floor
                         AND (is_value - oos_balance_ratio) <= :drawdown_limit
                        THEN 1 ELSE 0 END) AS generalised,
                    SUM(CASE
                        WHEN oos_balance_ratio < :floor
                          OR (is_value - oos_balance_ratio) > :drawdown_limit
                        THEN 1 ELSE 0 END) AS overfit
                FROM out_of_sample_evaluation
                WHERE study_name = :study_name
                GROUP BY start_timestamp, end_timestamp
                ORDER BY start_timestamp
            """)
            rows = session.execute(query, {
                'study_name': study_name,
                'floor': floor,
                'drawdown_limit': drawdown_limit,
            }).fetchall()
            return [
                OosWindowAggregate(
                    start=row[0],
                    end=row[1],
                    best_oos=row[2],
                    generalised_count=int(row[3]),
                    overfit_count=int(row[4]),
                )
                for row in rows
            ]
