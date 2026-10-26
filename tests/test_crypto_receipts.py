import unittest

SIG='3'*88
WALLET='2'*32


class CryptoReceiptTests(unittest.TestCase):
    def module(self):
        try:from bountyforge import crypto_receipts as m
        except ImportError:self.fail('Read-only crypto transaction verification is missing')
        return m

    def native(self):
        tx={'slot':10,'transaction':{'signatures':[SIG],'message':{'accountKeys':['4'*32,WALLET]}},
            'meta':{'err':None,'preBalances':[100,0],'postBalances':[90,10]}}
        status={'value':[{'slot':10,'err':None,'confirmationStatus':'finalized'}]}
        return tx,status

    def test_finality_signature_recipient_and_net_delta_are_all_required(self):
        m=self.module();tx,status=self.native();r=m.parse_finalized(tx,status,SIG,WALLET,'SOL')
        self.assertEqual(r['amount_base_units'],10);self.assertEqual(r['decimals'],9)
        self.assertFalse(r['owner_control_attested']);self.assertIsNone(r['spendable_usd'])
        for mode in ('pending','failed','wrong_signature','outgoing'):
            t,s=self.native()
            if mode=='pending':s['value'][0]['confirmationStatus']='confirmed'
            if mode=='failed':t['meta']['err']={'failure':1}
            if mode=='wrong_signature':t['transaction']['signatures']=['5'*88]
            if mode=='outgoing':t['meta']['postBalances'][1]=0
            with self.assertRaises(ValueError):m.parse_finalized(t,s,SIG,WALLET,'SOL')

    def test_usdc_requires_official_mint_owner_and_exact_integer_units(self):
        m=self.module();t,s=self.native()
        t['meta']['preTokenBalances']=[]
        row={'accountIndex':1,'owner':WALLET,'mint':m.USDC_SOLANA,'uiTokenAmount':{'amount':'1000000','decimals':6}}
        t['meta']['postTokenBalances']=[row]
        self.assertEqual(m.parse_finalized(t,s,SIG,WALLET,'USDC')['amount_base_units'],1000000)
        row['mint']='counterfeit'
        with self.assertRaises(ValueError):m.parse_finalized(t,s,SIG,WALLET,'USDC')

    def test_only_documented_read_rpc_methods_are_available(self):
        m=self.module();c=m.SolanaReadOnly()
        from unittest.mock import patch
        with patch.object(c.opener,'open',side_effect=AssertionError('No network')):
            for method in ('sendTransaction','requestAirdrop','signTransaction','simulateTransaction'):
                with self.assertRaises(ValueError):c.rpc(method,[])

    def test_missing_transaction_is_uncertain_not_received_or_automatically_reorged(self):
        m=self.module();_,s=self.native()
        with self.assertRaisesRegex(ValueError,'UNCONFIRMED_OR_PRUNED'):m.parse_finalized(None,s,SIG,WALLET,'SOL')
