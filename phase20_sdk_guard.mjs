// Owned capability observer and bounded request policy; no repair content.
import { readFileSync } from 'node:fs';
export const name='bountyforge-native-local-policy';
export const inject=['tools','systemPrompt'];
export function apply(ctx) {
  const policy=JSON.parse(readFileSync('/workspace/agent-policy.json','utf8'));
  if (![1,2].includes(policy.request_limit) || typeof policy.system!=='string') throw Error('Invalid owned policy');
  ctx.systemPrompt.section({name:'bountyforge-bounded-repair',order:0,complete:true,
    interpolate:false,text:policy.system});
  ctx.systemPrompt.suppressRuntimeContext();
  let agents=0;
  ctx.on('agent/created',async ({agent})=>{
    if (++agents!==1) throw Error('One owned agent only');
    const tools=ctx.get('tools');
    const forbidden=['bash','pwsh','exec_command','write_stdin','write','edit','read','read_image',
      'list_mcp_resources','list_mcp_resource_templates','read_mcp_resource','run_code'];
    const names=tools.schemas(agent).map(x=>x.name).sort(),refusals=[];
    for (const tool of forbidden) {
      const available=tools.resolveExecution(tool,agent,false)!==undefined;
      if (available) throw Error('Forbidden tool exposed');
      const result=await tools.execute({name:tool,arguments:{},agent,callId:'bf20-negative-'+tool,
        signal:AbortSignal.timeout(1000)});
      refusals.push({tool,available:false,invoked:true,unknown_tool:JSON.stringify(result).includes('UNKNOWN_TOOL')});
    }
    if (names.length || refusals.some(r=>!r.unknown_tool) || ctx.get('mcpResources')!==undefined)
      throw Error('Owned tool surface not empty');
    const credentialNames=['GH_TOKEN','GITHUB_TOKEN','GROQ_API_KEY','OPENAI_API_KEY','DEEPSEEK_API_KEY',
      'STRIPE_SECRET_KEY','AWS_SECRET_ACCESS_KEY','ANTHROPIC_API_KEY'].filter(n=>process.env[n]);
    if (credentialNames.length) throw Error('Credentials forbidden');
    process.stderr.write('BOUNTYFORGE_LIVE_AUDIT '+JSON.stringify({tool_names:names,refusals,
      mcp_resources_service_present:false,credential_names_present:credentialNames})+'\n');
    let count=0;
    agent.ctx.on('agent/request',async (_payload,next)=>{
      if (++count>policy.request_limit) throw Error('Owned inference request budget exhausted');
      if (tools.schemas(agent).length) throw Error('Tool surface changed');
      const config=await next();
      if (config.provider!=='bountyforge-local-qwen' || config.model!=='bountyforge-qwen-1.5b' || config.maxTokens!==150)
        throw Error('Owned local provider identity or budget changed');
      process.stderr.write('BOUNTYFORGE_SDK_REQUEST '+JSON.stringify({count,provider:config.provider,
        model:config.model,maxTokens:config.maxTokens})+'\n');
      return config;
    });
  });
}
