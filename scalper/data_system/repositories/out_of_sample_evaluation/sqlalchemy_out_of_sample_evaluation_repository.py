from dataclasses import asdict

from sqlalchemy import text

from data_system.clients import SQLAlchemyClient
from data_system.models import OutOfSampleEvaluation
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
                (study_name, trial_number, start_timestamp, end_timestamp, geo_mean_return)
                VALUES (:study_name, :trial_number, :start_timestamp, :end_timestamp, :geo_mean_return)
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
                SELECT study_name, trial_number, start_timestamp, end_timestamp, geo_mean_return
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
                    geo_mean_return=row[4],
                )
                for row in result.fetchall()
            ]
