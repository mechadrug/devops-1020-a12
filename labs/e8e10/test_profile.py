import json, tempfile, unittest
from pathlib import Path
from lab import fixture,scan,patch,commit

class ProfileTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.p=Path(self.tmp.name)/'sample';fixture(self.p)

    def test_independent_known_edges(self):
        r=scan(self.p)
        self.assertEqual(r['actual']['main.o'],['config.h','main.c'])
        self.assertEqual({(f['type'],f['dependency']) for f in r['findings']},{('MISSING','config.h'),('REDUNDANT','unused.h')})

    def test_unchanged_reuses_both_targets(self):
        r=scan(self.p,scan(self.p));self.assertEqual(r['reused'],['main.o','helper.o']);self.assertEqual(r['refreshed'],[])

    def test_include_added_invalidates_cache(self):
        old=scan(self.p)
        (self.p/'main.c').write_text('#include "extra.h"\n'+(self.p/'main.c').read_text());commit(self.p,'new include')
        r=scan(self.p,old)
        self.assertIn(['MISSING','main.o','extra.h'],r['added']);self.assertEqual(len(r['refreshed']),2)

    def test_patch_preserves_redundant_dependency(self):
        r=scan(self.p);diff,plan=patch(self.p,r)
        self.assertIn('+main.o: main.c unused.h config.h',diff)
        self.assertNotIn('-\tgcc',diff)
        self.assertNotIn('config.h',(self.p/'Makefile').read_text())

    def test_old_report_rejected(self):
        r=scan(self.p);r['commit']='0'*40
        with self.assertRaisesRegex(ValueError,'STALE_REPORT'):patch(self.p,r)

    def test_unsafe_dependency_rejected(self):
        r=scan(self.p);r['findings']=[{'type':'MISSING','target':'main.o','dependency':'../outside.h'}]
        with self.assertRaisesRegex(ValueError,'UNSAFE_PATH'):patch(self.p,r)

    def test_unsupported_configuration_rejected(self):
        (self.p/'Makefile').write_text((self.p/'Makefile').read_text().replace('-O0','-include unknown.h'))
        with self.assertRaisesRegex(ValueError,'UNSUPPORTED_FLAGS'):scan(self.p)

class StudentE8A231880398(unittest.TestCase):
    def test_declaration_change_reuses_actual_graph(self):
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory)/'sample'
            fixture(p)
            old=scan(p)
            f=p/'Makefile'
            f.write_text(f.read_text().replace('main.c unused.h','main.c unused.h config.h'))
            commit(p,'student: add missing declaration')
            result=scan(p,old)
            self.assertEqual(result['actual'],old['actual'])
            self.assertEqual(set(result['reused']),{'main.o','helper.o'})
            self.assertEqual(result['refreshed'],[])
            self.assertEqual(
                {(x['type'],x['target'],x['dependency']) for x in result['findings']},
                {('REDUNDANT','main.o','unused.h')})

class StudentE9A231880398(unittest.TestCase):
    def test_header_include_invalidates_and_refreshes(self):
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory)/'sample'
            fixture(p)
            old=scan(p)
            f=p/'main.c'
            f.write_text('#include "extra.h"\n'+f.read_text())
            commit(p,'student: add include')
            result=scan(p,old)
            self.assertIn('extra.h', result['actual']['main.o'])
            self.assertIn('main.o', result['refreshed'])
            self.assertEqual(result['reused'], [])
            self.assertNotEqual(result.get('status'), 'ERROR')

class StudentE10A231880398(unittest.TestCase):
    def test_transitive_include_incremental_equals_full(self):
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory)/'sample'
            fixture(p)
            old=scan(p)
            (p/'config.h').write_text('#include "extra.h"\n#define VALUE 1\n')
            commit(p,'student: transitive include')
            inc=scan(p,old); full=scan(p)
            self.assertEqual(inc['actual'], full['actual'])
            self.assertEqual(inc['declared'], full['declared'])
            self.assertEqual(
                {(f['type'],f['target'],f['dependency']) for f in inc['findings']},
                {(f['type'],f['target'],f['dependency']) for f in full['findings']},
            )


class StudentA231880138(unittest.TestCase):
    def test_transitive_header_body_change_reuses_known_edges(self):
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory)/'sample'
            fixture(p)
            (p/'config.h').write_text('#include "extra.h"\n#define VALUE 1\n')
            (p/'extra.h').write_text('static inline int extra(void){return 0;}\n')
            commit(p,'231880138: transitive header baseline')
            old=scan(p)
            (p/'extra.h').write_text('static inline int extra(void){return 0+0;}\n')
            commit(p,'231880138: header body only')
            result=scan(p,old)
            self.assertEqual(result['actual'],{
                'main.o':['config.h','extra.h','main.c'], 'helper.o':['helper.c']})
            self.assertEqual(result['reused'],['main.o','helper.o'])
            self.assertEqual(result['refreshed'],[])
            self.assertEqual(result['added'],[])
            self.assertEqual(result['resolved'],[])
            self.assertEqual({(f['type'],f['target'],f['dependency']) for f in result['findings']},{
                ('MISSING','main.o','config.h'), ('MISSING','main.o','extra.h'),
                ('REDUNDANT','main.o','unused.h')})

    def test_removing_transitive_header_resolves_only_its_missing_edge(self):
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory)/'sample'
            fixture(p)
            (p/'config.h').write_text('#include "extra.h"\n#define VALUE 1\n')
            (p/'extra.h').write_text('#include "leaf.h"\n#define EXTRA 0\n')
            (p/'leaf.h').write_text('#define LEAF 7\n')
            commit(p,'231880138: three-header baseline')
            old=scan(p)
            (p/'extra.h').write_text('#define EXTRA 0\n')
            (p/'leaf.h').unlink()
            commit(p,'231880138: remove transitive include and file')
            result=scan(p,old)
            self.assertEqual(result['actual'],{
                'main.o':['config.h','extra.h','main.c'], 'helper.o':['helper.c']})
            self.assertEqual(result['refreshed'],['main.o','helper.o'])
            self.assertEqual(result['reused'],[])
            self.assertEqual(result['added'],[])
            self.assertEqual(result['resolved'],[['MISSING','main.o','leaf.h']])
            self.assertEqual({(f['type'],f['target'],f['dependency']) for f in result['findings']},{
                ('MISSING','main.o','config.h'), ('MISSING','main.o','extra.h'),
                ('REDUNDANT','main.o','unused.h')})

    def test_transitive_declaration_cleanup_reuses_graph_and_resolves_all_findings(self):
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory)/'sample'
            fixture(p)
            (p/'config.h').write_text('#include "extra.h"\n#define VALUE 1\n')
            (p/'extra.h').write_text('#include "leaf.h"\n#define EXTRA 0\n')
            (p/'leaf.h').write_text('#define LEAF 7\n')
            commit(p,'231880138: declaration cleanup baseline')
            old=scan(p)
            makefile=p/'Makefile'
            makefile.write_text(makefile.read_text().replace(
                'main.o: main.c unused.h','main.o: main.c config.h extra.h leaf.h'))
            commit(p,'231880138: declare transitive headers and remove unused edge')
            result=scan(p,old)
            full=scan(p)
            expected={'main.o':['config.h','extra.h','leaf.h','main.c'],'helper.o':['helper.c']}
            self.assertEqual(result['actual'],expected)
            self.assertEqual(result['declared'],expected)
            self.assertEqual(result['reused'],['main.o','helper.o'])
            self.assertEqual(result['refreshed'],[])
            self.assertEqual(result['findings'],[])
            self.assertEqual(result['added'],[])
            self.assertEqual({tuple(x) for x in result['resolved']},{
                ('MISSING','main.o','config.h'), ('MISSING','main.o','extra.h'),
                ('MISSING','main.o','leaf.h'), ('REDUNDANT','main.o','unused.h')})
            for key in ['actual','declared','findings']:
                self.assertEqual(result[key],full[key])


class StudentE8A231880224(unittest.TestCase):
    def test_declaration_cleanup_reuses_actual_graph(self):
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory)/'sample'; fixture(p)
            old=scan(p)
            makefile=p/'Makefile'
            makefile.write_text(makefile.read_text().replace(
                'main.o: main.c unused.h','main.o: main.c config.h'))
            commit(p,'student: declare config and drop unused')
            result=scan(p,old)
            self.assertEqual(result['actual'],old['actual'])
            self.assertEqual(result['declared']['main.o'],['config.h','main.c'])
            self.assertEqual(result['reused'],['main.o','helper.o'])
            self.assertEqual(result['refreshed'],[])
            self.assertEqual(result['findings'],[])
            self.assertEqual({tuple(x) for x in result['resolved']},{
                ('MISSING','main.o','config.h'),('REDUNDANT','main.o','unused.h')})


class StudentE9A231880224(unittest.TestCase):
    def test_indirect_header_chain_invalidates_cache(self):
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory)/'sample'; fixture(p)
            old=scan(p)
            (p/'config.h').write_text('#include "extra.h"\n#define VALUE 1\n')
            (p/'extra.h').write_text('#include "leaf.h"\n#define EXTRA 0\n')
            (p/'leaf.h').write_text('#define LEAF 7\n')
            commit(p,'student: header chain adds leaf')
            result=scan(p,old); full=scan(p)
            self.assertEqual(result['actual']['main.o'],['config.h','extra.h','leaf.h','main.c'])
            self.assertEqual(result['reused'],[])
            self.assertEqual(set(result['refreshed']),{'main.o','helper.o'})
            self.assertEqual({tuple(x) for x in result['added']},{
                ('MISSING','main.o','extra.h'),('MISSING','main.o','leaf.h')})
            for key in ['actual','declared','findings']:
                self.assertEqual(result[key],full[key])


class StudentE10A231880224(unittest.TestCase):
    def test_flags_change_refresh_matches_full_five_times(self):
        from statistics import median
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory)/'sample'; fixture(p)
            old=scan(p)
            makefile=p/'Makefile'
            makefile.write_text(makefile.read_text().replace('-O0','-O1'))
            commit(p,'student: switch optimisation level')
            incremental=[]; full_times=[]
            for _ in range(5):
                incremental_result=scan(p,old); full_result=scan(p)
                for key in ['actual','declared','findings']:
                    self.assertEqual(incremental_result[key],full_result[key])
                self.assertEqual(incremental_result['reused'],[])
                self.assertEqual(incremental_result['refreshed'],['main.o','helper.o'])
                self.assertEqual({(x['type'],x['target'],x['dependency']) for x in incremental_result['findings']},
                    {('MISSING','main.o','config.h'),('REDUNDANT','main.o','unused.h')})
                incremental.append(incremental_result['elapsed_s'])
                full_times.append(full_result['elapsed_s'])
            self.assertGreater(median(incremental),0)
            print('STUDENT_E10_MEDIANS',median(incremental),median(full_times))


if __name__=='__main__':unittest.main()
