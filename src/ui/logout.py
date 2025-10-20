from flask import redirect


def main(self):
    if self.session.get("user"):
        self.log(
            message=f"Logout {self.session['user']['CodMember']} | {self.session['user']['NombreCompleto']} | {self.session['user']['DocNum']} | {self.session['user']['Correo']}"
        )
    self.session.clear()
    return redirect("login")
