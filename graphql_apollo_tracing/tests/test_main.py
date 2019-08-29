import graphene
from graphene import Schema
from graphql_apollo_tracing import TracingGQLBackend


def get_file_by_id(id):
    return File(**{'id': id, 'name': 'test_name'})


class File(graphene.ObjectType):
    id = graphene.Int(required=True)
    name = graphene.String()

    def resolve_id(self, info, **kwargs):
        return 1

    def resolve_name(self, info, **kwargs):
        return "name_%s" % self.id


class Query(graphene.ObjectType):
    files = graphene.List(
        graphene.NonNull(File),
        ids=graphene.List(graphene.NonNull(graphene.Int), required=True)
    )

    def resolve_files(self, info, ids, **kwargs):
        return [get_file_by_id(id_) for id_ in ids]


schema = Schema(query=Query)


def test_positive():
    query = '''
        query {
          files(ids:[1,2,3]) {
             id
             name
          }
        }
    '''
    result = schema.execute(query, backend=TracingGQLBackend(enable_ftv1_tracing=True))
    assert len(result.data['files']) == 3
    assert result.data['files'][0]['id'] == 1
    assert result.errors is None
    assert result.extensions['ftv1']
    assert len(result.extensions['ftv1']) > 200

# todo test redefine enabled
# test disabled
# try/except add
# limit depth
# test format?