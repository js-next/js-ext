import json
from jumpscale.servers.gedis.baseactor import BaseActor, actor_method
from jumpscale.god import j
from jumpscale.core.exceptions import JSException
from jumpscale.sals.reservation_chatflow.models import SolutionType


class Solutions(BaseActor):
    @actor_method
    def list_solutions(self, solution_type:str) -> str:
        # Update the solutions from the explorer
        j.sals.reservation_chatflow.get_solutions_explorer()
        
        solutions = []
        solutions = j.sals.reservation_chatflow.get_solutions(SolutionType[solution_type])
        return j.data.serializers.json.dumps({"data":solutions})

    @actor_method
    def cancel_solution(self, solution_type, solution_name) -> bool:
        if solution_type:
            j.sals.reservation_chatflow.cancel_solution_reservation(SolutionType[solution_type],solution_name)
            return True
        return False

Actor = Solutions