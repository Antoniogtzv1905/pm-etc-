from typing import List, Optional
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.openapi.utils import get_openapi
from sqlmodel import Session, select
from sqlalchemy import func

from .base_datos import inicializar_bd, obtener_sesion
from .models import User, Patient, Appointment
from .esquemas import (
    Token, UserCreate, UserOut,
    PatientCreate, PatientOut,
    AppointmentCreate, AppointmentOut,
)
from .auth import (
    hash_password, verify_password,
    crear_token_acceso, obtener_usuario_actual
)

app = FastAPI(
    title="MedApp API",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup_event():
    inicializar_bd()

@app.get("/health", tags=["Sistema"])
def estado():
    return {"status": "ok"}


@app.post("/auth/register", response_model=UserOut, tags=["Autenticación"])
def registrar_usuario(usuario: UserCreate, session: Session = Depends(obtener_sesion)):
    existe = session.exec(select(User).where(User.email == usuario.email)).first()
    if existe:
        raise HTTPException(status_code=400, detail="Email ya registrado")
    u = User(name=usuario.name, email=usuario.email, password_hash=hash_password(usuario.password))
    session.add(u)
    session.commit()
    session.refresh(u)
    return UserOut(id=u.id, name=u.name, email=u.email)

@app.post("/auth/login", response_model=Token, tags=["Autenticación"])
def iniciar_sesion(form: OAuth2PasswordRequestForm = Depends(), session: Session = Depends(obtener_sesion)):
    u = session.exec(select(User).where(User.email == form.username)).first()
    if not u or not verify_password(form.password, u.password_hash):
        raise HTTPException(status_code=401, detail="Credenciales inválidas")
    token = crear_token_acceso({"sub": str(u.id)})
    return Token(access_token=token)


@app.get("/patients", response_model=List[PatientOut], tags=["Pacientes"])
def listar_pacientes(
    search: Optional[str] = None,
    user: User = Depends(obtener_usuario_actual),
    session: Session = Depends(obtener_sesion),
):
    q = select(Patient)
    if search:
        q = q.where(func.lower(Patient.name).like(f"%{search.lower()}%"))
    return session.exec(q).all()

@app.post("/patients", response_model=PatientOut, tags=["Pacientes"])
def crear_paciente(
    p: PatientCreate,
    user: User = Depends(obtener_usuario_actual),
    session: Session = Depends(obtener_sesion),
):
    pac = Patient(**p.dict())
    session.add(pac)
    session.commit()
    session.refresh(pac)
    return PatientOut(**pac.dict())

@app.get("/patients/{pid}", response_model=PatientOut, tags=["Pacientes"])
def obtener_paciente(
    pid: int,
    user: User = Depends(obtener_usuario_actual),
    session: Session = Depends(obtener_sesion),
):
    pac = session.get(Patient, pid)
    if not pac:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    return PatientOut(**pac.dict())

@app.put("/patients/{pid}", response_model=PatientOut, tags=["Pacientes"])
def actualizar_paciente(
    pid: int,
    p: PatientCreate,
    user: User = Depends(obtener_usuario_actual),
    session: Session = Depends(obtener_sesion),
):
    pac = session.get(Patient, pid)
    if not pac:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    for k, v in p.dict().items():
        setattr(pac, k, v)
    session.add(pac)
    session.commit()
    session.refresh(pac)
    return PatientOut(**pac.dict())

@app.delete("/patients/{pid}", tags=["Pacientes"])
def eliminar_paciente(
    pid: int,
    user: User = Depends(obtener_usuario_actual),
    session: Session = Depends(obtener_sesion),
):
    pac = session.get(Patient, pid)
    if not pac:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    session.delete(pac)
    session.commit()
    return {"ok": True}

@app.get("/patients/{pid}/appointments", response_model=List[AppointmentOut], tags=["Citas"])
def listar_citas(
    pid: int,
    user: User = Depends(obtener_usuario_actual),
    session: Session = Depends(obtener_sesion),
):
    return session.exec(select(Appointment).where(Appointment.patient_id == pid)).all()

@app.post("/patients/{pid}/appointments", response_model=AppointmentOut, tags=["Citas"])
def crear_cita(
    pid: int,
    ap: AppointmentCreate,
    user: User = Depends(obtener_usuario_actual),
    session: Session = Depends(obtener_sesion),
):
    if not session.get(Patient, pid):
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    cita = Appointment(patient_id=pid, **ap.dict())
    session.add(cita)
    session.commit()
    session.refresh(cita)
    return AppointmentOut(**cita.dict())

@app.put("/appointments/{aid}", response_model=AppointmentOut, tags=["Citas"])
def actualizar_cita(
    aid: int,
    ap: AppointmentCreate,
    user: User = Depends(obtener_usuario_actual),
    session: Session = Depends(obtener_sesion),
):
    cita = session.get(Appointment, aid)
    if not cita:
        raise HTTPException(status_code=404, detail="Cita no encontrada")
    for k, v in ap.dict().items():
        setattr(cita, k, v)
    session.add(cita)
    session.commit()
    session.refresh(cita)
    return AppointmentOut(**cita.dict())

@app.delete("/appointments/{aid}", tags=["Citas"])
def eliminar_cita(
    aid: int,
    user: User = Depends(obtener_usuario_actual),
    session: Session = Depends(obtener_sesion),
):
    cita = session.get(Appointment, aid)
    if not cita:
        raise HTTPException(status_code=404, detail="Cita no encontrada")
    session.delete(cita)
    session.commit()
    return {"ok": True}



def openapi_sin_descripciones():
    if app.openapi_schema:
        return app.openapi_schema
    schema = get_openapi(title=app.title, version=app.version, routes=app.routes)
    for path in schema.get("paths", {}).values():
        for method in path.values():
            method.pop("summary", None)
            method.pop("description", None)
    app.openapi_schema = schema
    return schema

app.openapi = openapi_sin_descripciones
