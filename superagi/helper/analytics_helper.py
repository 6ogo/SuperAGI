from typing import List, Dict, Tuple, Optional, Iterator, Union, Any
from sqlalchemy.orm import Session
from sqlalchemy.orm.query import Query
from superagi.models.events import Event
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import text, func, Integer
from collections import defaultdict
import logging

class AnalyticsHelper:

    def __init__(self, session: Session):
        self.session = session

    def create_event(self, event_name: str, event_value: int, json_property: dict, agent_id: int, org_id: int) -> Optional[Event]:
        try:
            event = Event(
                event_name=event_name,
                event_value=event_value,
                json_property=json_property,
                agent_id=agent_id,
                org_id=org_id,
            )
            self.session.add(event)
            self.session.commit()
            return event
        except SQLAlchemyError as err:
            logging.error(f"Error while creating event: {str(err)}")
            return None

    def calculate_run_completed_metrics(self) -> Dict[str, Dict[str, Union[int, List[Dict[str, int]]]]]:

        agent_model_query = self.session.query(
            Event.json_property['model'].label('model'),
            Event.agent_id
        ).filter_by(event_name="agent_created").subquery()

        agent_runs_query = self.session.query(
            agent_model_query.c.model,
            func.count(Event.id).label('runs')
        ).join(Event, Event.agent_id == agent_model_query.c.agent_id).filter_by(event_name="run_completed").group_by(agent_model_query.c.model).subquery()

        agent_tokens_query = self.session.query(
            agent_model_query.c.model,
            func.sum(text("(json_property->>'tokens_consumed')::int")).label('tokens')
        ).join(Event, Event.agent_id == agent_model_query.c.agent_id).filter_by(event_name="run_completed").group_by(agent_model_query.c.model).subquery()

        agent_count_query = self.session.query(
            agent_model_query.c.model,
            func.count(agent_model_query.c.agent_id).label('agents')
        ).group_by(agent_model_query.c.model).subquery()

        agents = self.session.query(agent_count_query).all()
        runs = self.session.query(agent_runs_query).all()
        tokens = self.session.query(agent_tokens_query).all()

        metrics = {
            'agent_details': {
                'total_agents': sum([item.agents for item in agents]),
                'model_metrics': [{'name': item.model, 'value': item.agents} for item in agents]
            },
            'run_details': {
                'total_runs': sum([item.runs for item in runs]),
                'model_metrics': [{'name': item.model, 'value': item.runs} for item in runs]
            },
            'tokens_details': {
                'total_tokens': sum([item.tokens for item in tokens]),
                'model_metrics': [{'name': item.model, 'value': item.tokens} for item in tokens]
            },
        }

        return metrics

    def fetch_agent_data(self) -> Dict[str, List[Dict[str, Any]]]:
        agent_subquery = self.session.query(
            Event.agent_id,
            Event.json_property['agent_name'].label('agent_name'),
            Event.json_property['model'].label('model')
        ).filter_by(event_name="agent_created").subquery()

        run_subquery = self.session.query(
            Event.agent_id,
            func.sum(text("(json_property->>'tokens_consumed')::int")).label('total_tokens'),
            func.sum(text("(json_property->>'calls')::int")).label('total_calls'),
            func.count(Event.id).label('runs_completed'),
        ).filter_by(event_name="run_completed").group_by(Event.agent_id).subquery()

        tool_subquery = self.session.query(
            Event.agent_id,
            func.array_agg(Event.json_property['tool_name'].distinct()).label('tools_used'),
        ).filter_by(event_name="tool_used").group_by(Event.agent_id).subquery()

        runs = self.session.query(
            Event.agent_id,
            Event.json_property['agent_execution_id'],
            Event.created_at, Event.event_name
        ).filter(Event.event_name.in_(["run_created", "run_completed"])).all()

        run_times = defaultdict(lambda: defaultdict(list))
        for agent_id, agent_execution_id, timestamp, event_name in runs:
            run_times[agent_id][agent_execution_id].append((event_name, timestamp))

        avg_run_times = defaultdict(list)
        for agent_id, events in run_times.items():
            for agent_execution_id, agent_events in events.items():
                if 'run_created' in [event_name for event_name, _ in agent_events] and \
                    'run_completed' in [event_name for event_name, _ in agent_events]:
                    run_created_time = next(time for event_name, time in agent_events if event_name == 'run_created')
                    run_completed_time = next(time for event_name, time in agent_events if event_name == 'run_completed')
                    avg_run_times[agent_id].append((run_completed_time - run_created_time).total_seconds())

        query = self.session.query(
            agent_subquery.c.agent_id,
            agent_subquery.c.agent_name,
            agent_subquery.c.model,
            run_subquery.c.total_tokens,
            run_subquery.c.total_calls,
            run_subquery.c.runs_completed,
            tool_subquery.c.tools_used
        ).outerjoin(run_subquery, run_subquery.c.agent_id == agent_subquery.c.agent_id) \
            .outerjoin(tool_subquery, tool_subquery.c.agent_id == agent_subquery.c.agent_id)

        result = query.all()

        agent_details = [{
            "name": row.agent_name,
            "agent_id": row.agent_id,
            "runs_completed": row.runs_completed,
            "total_calls": row.total_calls,
            "total_tokens": row.total_tokens,
            "tools_used": row.tools_used,
            "model_name": row.model,
            "avg_run_time": sum(avg_run_times[row.agent_id]) / len(avg_run_times[row.agent_id]) if avg_run_times[row.agent_id] else 0
        } for row in result]

        return {'agent_details': agent_details}

    def fetch_agent_runs(self, agent_id: int) -> List[Dict[str, int]]:
        agent_runs = []
        completed_subquery = self.session.query(
            Event.json_property['agent_execution_id'].label('completed_agent_execution_id'),
            Event.json_property['tokens_consumed'].label('tokens_consumed'),
            Event.json_property['calls'].label('calls'),
            Event.updated_at
        ).filter_by(event_name="run_completed", agent_id=agent_id).subquery()

        created_subquery = self.session.query(
            Event.json_property['agent_execution_id'].label('created_agent_execution_id'),
            Event.json_property['agent_execution_name'].label('agent_execution_name'),
            Event.created_at
        ).filter_by(event_name="run_created", agent_id=agent_id).subquery()

        query = self.session.query(
            created_subquery.c.agent_execution_name,
            completed_subquery.c.tokens_consumed,
            completed_subquery.c.calls,
            created_subquery.c.created_at,
            completed_subquery.c.updated_at
        ).join(completed_subquery, completed_subquery.c.completed_agent_execution_id == created_subquery.c.created_agent_execution_id)

        result = query.all()

        agent_runs = [{
            'name': row.agent_execution_name,
            'tokens_consumed': int(row.tokens_consumed) if row.tokens_consumed else 0,
            'calls': int(row.calls) if row.calls else 0,
            'created_at': row.created_at,
            'updated_at': row.updated_at
        } for row in result]

        return agent_runs


    def get_active_runs(self) -> List[Dict[str, str]]:
        running_executions = []
        completed_subquery = self.session.query(
            Event.json_property['agent_execution_id'].label('agent_execution_id'),
        ).filter_by(event_name="run_completed").subquery()

        start_subquery = self.session.query(
            Event.json_property['agent_execution_id'].label('agent_execution_id'),
            Event.json_property['agent_execution_name'].label('agent_execution_name'),
            Event.created_at,
            Event.agent_id
        ).filter_by(event_name="run_created").subquery()

        agent_created_subquery = self.session.query(
            Event.json_property['agent_name'].label('agent_name'),
            Event.agent_id
        ).filter_by(event_name="agent_created").subquery()

        query = self.session.query(
            start_subquery.c.agent_execution_name,
            start_subquery.c.created_at,
            agent_created_subquery.c.agent_name
        ).select_from(start_subquery)

        query = query.outerjoin(completed_subquery, start_subquery.c.agent_execution_id == completed_subquery.c.agent_execution_id).filter(completed_subquery.c.agent_execution_id == None)

        query = query.join(agent_created_subquery, start_subquery.c.agent_id == agent_created_subquery.c.agent_id)

        result = query.all()

        running_executions = [{
            'name': row.agent_execution_name,
            'created_at': row.created_at,
            'agent_name': row.agent_name or 'Unknown',
        } for row in result]

        return running_executions

    def calculate_tool_usage(self) -> List[Dict[str, int]]:
            tool_usage = []
            tool_used_subquery = self.session.query(
                Event.json_property['tool_name'].label('tool_name'),
                Event.agent_id
            ).filter_by(event_name="tool_used").subquery()

            agent_count = self.session.query(
                tool_used_subquery.c.tool_name,
                func.count(func.distinct(tool_used_subquery.c.agent_id)).label('unique_agents')
            ).group_by(tool_used_subquery.c.tool_name).subquery()

            total_usage = self.session.query(
                tool_used_subquery.c.tool_name,
                func.count(tool_used_subquery.c.tool_name).label('total_usage')
            ).group_by(tool_used_subquery.c.tool_name).subquery()

            query = self.session.query(
                agent_count.c.tool_name,
                agent_count.c.unique_agents,
                total_usage.c.total_usage
            ).join(total_usage, total_usage.c.tool_name == agent_count.c.tool_name)

            result = query.all()

            tool_usage = [{
                'tool_name': row.tool_name,
                'unique_agents': row.unique_agents,
                'total_usage': row.total_usage
            } for row in result]

            return tool_usage