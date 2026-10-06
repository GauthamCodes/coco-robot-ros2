"""Live ROS endpoint evidence. Graph discovery absence is never a proof by itself."""


def snapshot(node):
    topics=node.get_topic_names_and_types()
    return {'nodes':[{'name':n,'namespace':s} for n,s in node.get_node_names_and_namespaces()],
            'topics':{topic:{'types':types,
                            'subscriptions':[{'name':e.node_name,'namespace':e.node_namespace}
                                             for e in node.get_subscriptions_info_by_topic(topic)],
                            'publishers':[{'name':e.node_name,'namespace':e.node_namespace}
                                          for e in node.get_publishers_info_by_topic(topic)]}
                      for topic,types in topics}}


def violations(graph,require_arbiter=True):
    bad=[]
    for topic,data in graph['topics'].items():
        if topic=='/eval' or topic.startswith('/eval/'):
            for end in data['subscriptions']:
                if end['namespace']!='/eval' and not end['namespace'].startswith('/eval/'):
                    bad.append({'invariant':'GROUND_TRUTH_ISOLATION','topic':topic,'endpoint':end})
    if require_arbiter:
        publishers=graph['topics'].get('/diff_drive_controller/cmd_vel',{}).get('publishers',[])
        if len(publishers)!=1 or publishers[0]['name']!='cmd_vel_arbiter':
            bad.append({'invariant':'I06','publishers':publishers})
    return bad
