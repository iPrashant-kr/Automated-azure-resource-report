import os
import argparse
import datetime as dt
from azure.identity import AzureCliCredential
from azure.mgmt.resource import SubscriptionClient
from azure.mgmt.resourcegraph import ResourceGraphClient
from azure.mgmt.resourcegraph.models import QueryRequest
from azure.mgmt.monitor import MonitorManagementClient
import pandas as pd
from tqdm import tqdm

def isoformat(dt_obj):
    return dt_obj.strftime("%Y-%m-%dT%H:%M:%SZ")

def get_clients():
    cred = AzureCliCredential()
    sub_client = SubscriptionClient(cred)
    rg_client = ResourceGraphClient(cred)
    return cred, sub_client, rg_client

def query_current_inventory(rg_client, subscription_ids):
    q = "Resources | project id, name, type, resourceGroup, subscriptionId, location, tags"
    req = QueryRequest(query=q, subscriptions=subscription_ids, options=None)
    resp = rg_client.resources(req)
    cols = [c.name for c in resp.data.columns]
    rows = [r for r in resp.data.rows]
    df = pd.DataFrame(rows, columns=cols)
    return df

def fetch_activity_logs_for_subscription(cred, subscription_id, start_dt, end_dt):
    mc = MonitorManagementClient(cred, subscription_id)
    f = f"eventTimestamp ge {isoformat(start_dt)} and eventTimestamp le {isoformat(end_dt)}"
    items = list(mc.activity_logs.list(filter=f))
    return items

def classify_activity_events(events):
    created = []
    deleted = []
    for e in events:
        ed = e.as_dict()
        op = ed.get('operation_name', {}).get('value', '').lower()
        status = ed.get('status', {}).get('value', '').lower()
        if status == 'succeeded':
            if 'delete' in op:
                deleted.append(ed)
            elif 'write' in op or 'create' in op or op.endswith('/write'):
                created.append(ed)
    return created, deleted

def extract_resource_from_event(evt):
    rid = evt.get('resource_id') or evt.get('resourceUri') or evt.get('resourceId')
    rg = evt.get('resource_group_name') or evt.get('resourceGroupName')
    rtype = evt.get('resource_provider', {}).get('value') if isinstance(evt.get('resource_provider'), dict) else None
    return rid, rg, rtype

def main(outdir='reports', days=30):
    os.makedirs(outdir, exist_ok=True)
    cred, sub_client, rg_client = get_clients()
    subs = [s.subscription_id for s in sub_client.subscriptions.list()]
    print(f"Found {len(subs)} subscriptions")

    inv_df = query_current_inventory(rg_client, subs)
    inv_df.to_csv(os.path.join(outdir, 'current_inventory.csv'), index=False)

    end_last = dt.datetime.utcnow()
    start_last = end_last - dt.timedelta(days=days)
    end_prev = start_last
    start_prev = end_prev - dt.timedelta(days=days)

    created_rows_last, created_rows_prev, deleted_rows_last = [], [], []

    for sub in tqdm(subs, desc='Subscriptions'):
        events_last = fetch_activity_logs_for_subscription(cred, sub, start_last, end_last)
        created_last, deleted_last = classify_activity_events(events_last)
        for e in created_last:
            rid, rg, rtype = extract_resource_from_event(e)
            created_rows_last.append({'subscriptionId': sub, 'resourceId': rid, 'resourceGroup': rg, 'resourceType': rtype, 'eventTimestamp': e.get('event_timestamp')})
        for e in deleted_last:
            rid, rg, rtype = extract_resource_from_event(e)
            deleted_rows_last.append({'subscriptionId': sub, 'resourceId': rid, 'resourceGroup': rg, 'resourceType': rtype, 'eventTimestamp': e.get('event_timestamp')})

        events_prev = fetch_activity_logs_for_subscription(cred, sub, start_prev, end_prev)
        created_prev, _ = classify_activity_events(events_prev)
        for e in created_prev:
            rid, rg, rtype = extract_resource_from_event(e)
            created_rows_prev.append({'subscriptionId': sub, 'resourceId': rid, 'resourceGroup': rg, 'resourceType': rtype, 'eventTimestamp': e.get('event_timestamp')})

    df_created_last = pd.DataFrame(created_rows_last).drop_duplicates()
    df_created_prev = pd.DataFrame(created_rows_prev).drop_duplicates()
    df_deleted_last = pd.DataFrame(deleted_rows_last).drop_duplicates()

    df_created_last.to_csv(os.path.join(outdir, 'created_last_30d.csv'), index=False)
    df_created_prev.to_csv(os.path.join(outdir, 'created_prev_30d.csv'), index=False)
    df_deleted_last.to_csv(os.path.join(outdir, 'deleted_last_30d.csv'), index=False)

    def aggregate(df, name):
        if df.empty:
            return pd.DataFrame()
        g = df.groupby(['subscriptionId','resourceType']).size().reset_index(name=name)
        return g

    agg_created_last = aggregate(df_created_last, 'created_last')
    agg_created_prev = aggregate(df_created_prev, 'created_prev')
    agg_deleted_last = aggregate(df_deleted_last, 'deleted_last')

    summary = pd.merge(agg_created_last, agg_created_prev, on=['subscriptionId','resourceType'], how='outer')
    summary = pd.merge(summary, agg_deleted_last, on=['subscriptionId','resourceType'], how='outer')
    summary = summary.fillna(0)
    summary['net_change'] = summary['created_last'] - summary['deleted_last']
    summary.to_csv(os.path.join(outdir, 'summary.csv'), index=False)

    print('Reports written to', outdir)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--outdir', default='reports')
    parser.add_argument('--days', type=int, default=30)
    args = parser.parse_args()
    main(outdir=args.outdir, days=args.days)
